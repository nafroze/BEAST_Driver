#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BEAST NTL Cyclone Disturbance Detector
Author: Afrozen (July 2025)
Description: Runs BEAST on NTL data per settlement, detects disturbances within ±60 days of cyclone, and generates plots + stats.
"""

import os, argparse
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless mode for server
import matplotlib.pyplot as plt
from datetime import timedelta
from scipy.stats import ttest_ind
from sklearn.metrics import r2_score, mean_squared_error
import Rbeast

# === Outlier detection ===
def detect_and_remove_outliers(data, threshold=3.5):
    z_scores = np.abs((data - data.mean()) / data.std())
    return data[z_scores < threshold]

# === Cohen's d calculation ===
def cohen_d(before, after):
    diff = np.mean(after) - np.mean(before)
    pooled_std = np.sqrt((np.std(before)**2 + np.std(after)**2) / 2)
    return diff / pooled_std

# === Core processor per settlement ===
def process_settlement(settlement_id, df_ntl, output_dir, summary_records, cyclone_date=None):
    # Subset data for this settlement
    its_data = df_ntl[df_ntl['settl_pcod'] == settlement_id].copy()
    its_data['NTLmean'] = detect_and_remove_outliers(its_data['NTLmean'])
    its_data.dropna(inplace=True)

    if its_data['NTLmean'].mean() < 0 or len(its_data) < 365:
        print(f"⚠️ Skipped {settlement_id}: insufficient brightness or data")
        return False

    try:
        beast_result = Rbeast.beast(its_data['NTLmean'].values, season='none', prior={'trendMinOrder': 0, 'trendMaxOrder': 1})
    except:
        return False

    # Extract change points
    raw_cps = np.array(getattr(beast_result.trend, 'cp', []))
    cps = raw_cps[~np.isnan(raw_cps)].astype(int)
    trend_values = np.array(getattr(beast_result.trend, 'Y', beast_result.trend))

    if len(cps) == 0:
        return False

    min_len = min(len(trend_values), len(its_data))
    its_data = its_data.iloc[:min_len]
    its_data['BEAST_Trend'] = trend_values[:min_len]
    its_data['Deviation'] = its_data['NTLmean'] - its_data['BEAST_Trend']

    cyclone_date = pd.to_datetime(cyclone_date)
    window_start = cyclone_date - timedelta(days=60)
    window_end = cyclone_date + timedelta(days=60)

    # Identify candidate disturbance CPs in window with negative drop
    window_cps = [i for i in cps if window_start <= its_data.index[i] <= window_end and trend_values[i + 1] < trend_values[i]]
    if len(window_cps) == 0:
        return False

    # Proceed with first valid disturbance in window
    disturbance_idx = window_cps[0]
    disturbance_date = its_data.index[disturbance_idx]

    pre_dev = its_data.loc[:disturbance_date]['Deviation'].dropna()
    post_dev = its_data.loc[disturbance_date:]['Deviation'].dropna()
    t_stat, p_val = ttest_ind(pre_dev, post_dev, equal_var=False)
    d_val = cohen_d(pre_dev, post_dev) if len(pre_dev) > 5 and len(post_dev) > 5 else np.nan

    if p_val > 0.05:
        return False

    # Detect recovery
    post_event = its_data.loc[disturbance_date:]
    recovery_date, recovery_duration = (post_event[post_event['Deviation'] >= 0].index[0],
                                        (post_event[post_event['Deviation'] >= 0].index[0] - disturbance_date).days) if (post_event['Deviation'] >= 0).any() else (np.nan, np.nan)

    # Save change points
    cp_df = pd.DataFrame({"ChangePoint_Index": cps, "Date": its_data.index[cps], "TrendBefore": trend_values[cps], "TrendAfter": trend_values[cps + 1]})
    cp_df.to_csv(os.path.join(output_dir, f"{settlement_id}_changepoints.csv"), index=False)

    # Save time series
    its_data.to_csv(os.path.join(output_dir, f"BEAST_NTL_{settlement_id}.csv"))

    # === PLOTTING ===

    # Full-range plot
    fig, ax1 = plt.subplots(figsize=(12, 4))
    ax1.plot(its_data.index, its_data['NTLmean'], '.', label='Observed', color='skyblue')
    ax1.plot(its_data.index, its_data['BEAST_Trend'], '-', label='BEAST Trend', color='navy')
    for i in cps:
        ax1.axvline(its_data.index[i], linestyle=':', color='red')
    ax1.axvline(cyclone_date, linestyle=':', color='blue', label='Cyclone Date')
    ax1.axvline(disturbance_date, linestyle='--', color='red', label='Disturbance')
    if isinstance(recovery_date, pd.Timestamp):
        ax1.axvline(recovery_date, linestyle='--', color='green', label='Recovery')
    ax1.legend()
    ax1.set_title(f"{settlement_id} | Full Range")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"BEAST_{settlement_id}_full.png"))
    plt.close()

    # Zoomed-in plot
    zoom_start = cyclone_date - timedelta(days=60)
    zoom_end = cyclone_date + timedelta(days=60)
    zoom_data = its_data.loc[zoom_start:zoom_end]

    fig, ax2 = plt.subplots(figsize=(12, 4))
    ax2.plot(zoom_data.index, zoom_data['NTLmean'], '.', color='skyblue')
    ax2.plot(zoom_data.index, zoom_data['BEAST_Trend'], '-', color='navy')
    for i in cps:
        cp_date = its_data.index[i]
        if zoom_start <= cp_date <= zoom_end:
            ax2.axvline(cp_date, linestyle=':', color='red')
    ax2.axvline(cyclone_date, linestyle=':', color='blue', label='Cyclone Date')
    ax2.axvline(disturbance_date, linestyle='--', color='red', label='Disturbance')
    if isinstance(recovery_date, pd.Timestamp) and zoom_start <= recovery_date <= zoom_end:
        ax2.axvline(recovery_date, linestyle='--', color='green', label='Recovery')
    ax2.legend()
    ax2.set_title(f"{settlement_id} | Zoom: ±60 Days Around Cyclone")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"BEAST_{settlement_id}_zoom.png"))
    plt.close()

    # === Stats Summary ===
    aligned = its_data[['NTLmean', 'BEAST_Trend']].dropna()
    r2 = r2_score(aligned['NTLmean'], aligned['BEAST_Trend'])
    rmse = np.sqrt(mean_squared_error(aligned['NTLmean'], aligned['BEAST_Trend']))

    summary_records.append({
        "Settlement ID": settlement_id,
        "R²": round(r2, 3),
        "RMSE": round(rmse, 3),
        "Detected Disturbance Date": disturbance_date.date(),
        "Recovery Duration (days)": recovery_duration if not pd.isna(recovery_duration) else "NA",
        "p-value (∆NTL)": round(p_val, 4),
        "Cohen's d": round(d_val, 4) if not pd.isna(d_val) else "NA",
        "All Change Points": ", ".join([its_data.index[int(i)].strftime('%Y-%m-%d') for i in cps if i < len(its_data)])
    })

    return True

# === MAIN ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data_dir", required=True)
    parser.add_argument("-o", "--output_dir", required=True)
    parser.add_argument("-l", "--settlement_list", required=True)
    parser.add_argument("-c", "--cyclone_date", required=True, help="Cyclone date (YYYY-MM-DD)")
    args = parser.parse_args()

    df_ntl = pd.read_csv(os.path.join(args.data_dir, "allNTL_allgrid3_props_gaps.csv"))
    df_ntl['YYYY_MM_DD'] = pd.to_datetime(df_ntl['YYYY_MM_DD'])
    df_ntl.set_index('YYYY_MM_DD', inplace=True)
    df_ntl['NTLmean'] = pd.to_numeric(df_ntl['NTLmean'], errors='coerce').fillna(0)

    os.makedirs(args.output_dir, exist_ok=True)
    settle_df = pd.read_csv(args.settlement_list)
    settlement_ids = settle_df['settle_pcod'].unique().tolist()

    summary_records = []
    processed = skipped = errors = 0

    for sid in settlement_ids:
        print(f"🔄 Processing: {sid}")
        try:
            success = process_settlement(sid, df_ntl, args.output_dir, summary_records, args.cyclone_date)
            if success:
                print(f"✅ Completed: {sid}")
                processed += 1
            else:
                print(f"⚠️ Skipped: {sid}")
                skipped += 1
        except Exception as e:
            print(f"❌ Error in {sid}: {e}")
            errors += 1

    pd.DataFrame(summary_records).to_csv(os.path.join(args.output_dir, "BEAST_Summary_All.csv"), index=False)

    print("\n📊 Summary Report:")
    print(f"   Total Settlements: {len(settlement_ids)}")
    print(f"   ✅ Processed (valid results): {processed}")
    print(f"   ⚠️ Skipped (not significant or low signal): {skipped}")
    print(f"   ❌ Errors during processing: {errors}")
