#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, argparse
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import timedelta
from scipy.stats import ttest_ind
from sklearn.metrics import r2_score, mean_squared_error
import Rbeast

# Define Cohen's d function
def cohen_d(before, after):
    diff = np.mean(after) - np.mean(before)
    pooled_std = np.sqrt((np.std(before)**2 + np.std(after)**2) / 2)
    return diff / pooled_std

def detect_and_remove_outliers(data, threshold=3.5):
    z_scores = np.abs((data - data.mean()) / data.std())
    return data[z_scores < threshold]

def process_settlement(settlement_id, df_ntl, output_dir, summary_records):
    disturbance_strength = "none"
    its_data = df_ntl[df_ntl['settl_pcod'] == settlement_id].copy()
    its_data['NTLmean'] = detect_and_remove_outliers(its_data['NTLmean'])
    its_data.dropna(inplace=True)

    # === Filter out low-brightness settlements
    if its_data['NTLmean'].mean() < 0.5:
        print(f"⚠️ Skipped {settlement_id}: mean NTL < 0.5 nW/cm²/sr")
        return False

    if len(its_data) < 100:
        return False

    try:
        beast_result = Rbeast.beast(its_data['NTLmean'].values, season='none',
                                    prior={'trendMinOrder': 0, 'trendMaxOrder': 1})
    except:
        return False

    cps = np.array(getattr(beast_result.trend, 'cp', [])).astype(int)
    trend_values = np.array(getattr(beast_result.trend, 'Y', beast_result.trend))
    its_data = its_data.iloc[:len(trend_values)]
    its_data['BEAST_Trend'] = trend_values
    its_data['Deviation'] = its_data['NTLmean'] - its_data['BEAST_Trend']

    known_cyclone_date = pd.to_datetime("2022-02-05")
    cp_dates = [its_data.index[i] for i in cps if i < len(its_data)]
    valid_cp_indices = [i for i, dt in zip(cps, cp_dates)
                        if abs((dt - known_cyclone_date).days) <= 60]

    if not valid_cp_indices:
        print("❌ No valid BEAST disturbance near cyclone date.")
        return False

    disturbance_idx = valid_cp_indices[0]
    drop_mag = trend_values[disturbance_idx + 1] - trend_values[disturbance_idx]
    if drop_mag >= 0:
        print(f"⚠️ BEAST CP at {its_data.index[disturbance_idx].date()} is an upward shift (Δ={drop_mag:.4f})")
        return False

    disturbance_date = its_data.index[disturbance_idx]

    # === t-test to confirm statistically significant drop
    pre_dev = its_data.loc[:disturbance_date]['Deviation'].dropna()
    post_dev = its_data.loc[disturbance_date:]['Deviation'].dropna()
    t_stat, p_value = ttest_ind(pre_dev, post_dev, equal_var=False)
    if p_value > 0.05:
        print("⚠️ No significant pre/post difference (t-test). Skipping.")
        return False

    # === Calculate Cohen's d
    d = cohen_d(pre_dev, post_dev)
    print(f"Cohen's d: {d}")

    # === Detect recovery CP ===
    recovery_cp = None
    recovery_window = 90
    for i in cps:
        if i > disturbance_idx and (i - disturbance_idx) <= recovery_window:
            delta = trend_values[i + 1] - trend_values[i] if i + 1 < len(trend_values) else 0
            if delta > 0.003:
                recovery_cp = {"idx": i, "date": its_data.index[i], "drop": delta}
                break

    recovery_cp_date = recovery_cp["date"] if recovery_cp else "NA"
    slope_recovery = (trend_values[disturbance_idx + recovery_window] - trend_values[disturbance_idx]) / recovery_window \
        if disturbance_idx + recovery_window < len(trend_values) else np.nan
    recovery_type = "CP" if recovery_cp else ("slope" if slope_recovery > 0.001 else "none")

    # === Create output folder only if valid disturbance ===
    settlement_dir = os.path.join(output_dir, settlement_id)
    os.makedirs(settlement_dir, exist_ok=True)

    # === Save time series and change points
    its_data.to_csv(os.path.join(settlement_dir, f"BEAST_NTL_{settlement_id}.csv"))
    pd.DataFrame({"ChangePoint_Index": cps}).to_csv(os.path.join(settlement_dir, f"{settlement_id}_changepoints.csv"), index=False)

    # === Zoomed plot (±100 days)
    zoom_window = 100
    zoom_data = its_data.loc[disturbance_date - pd.Timedelta(days=zoom_window): disturbance_date + pd.Timedelta(days=zoom_window)]

    fig, axz = plt.subplots(figsize=(10, 4))
    axz.plot(zoom_data.index, zoom_data['NTLmean'], '.', color='skyblue', label='Observed')
    axz.plot(zoom_data.index, zoom_data['BEAST_Trend'], '-', color='navy', label='BEAST Trend')
    axz.axvline(disturbance_date, linestyle='--', color='red', label='Disturbance')
    axz.axvline(known_cyclone_date, linestyle=':', color='black', linewidth=1.5, label='Cyclone Date')

    ytop = axz.get_ylim()[1] * 0.9
    axz.text(disturbance_date, ytop,
             f"Dist: {disturbance_date.strftime('%Y-%m-%d')}",
             color='red', fontsize=9, ha='left', va='top', rotation=90)

    if recovery_cp:
        axz.axvline(recovery_cp["date"], linestyle='--', color='green', label='Recovery')
        axz.axvspan(disturbance_date, recovery_cp["date"], color='lightcoral', alpha=0.3, label='Disturbance Phase')
        axz.axvspan(recovery_cp["date"], recovery_cp["date"] + pd.Timedelta(days=30),
                    color='lightgreen', alpha=0.2, label='Recovery Phase')
        axz.text(recovery_cp["date"], ytop,
                 f"Recov: {recovery_cp['date'].strftime('%Y-%m-%d')}",
                 color='green', fontsize=9, ha='left', va='top', rotation=90)
    elif slope_recovery > 0.001:
        recovery_date = disturbance_date + pd.Timedelta(days=recovery_window)
        axz.axvline(recovery_date, linestyle='--', color='green', label='Slope Recovery')
        axz.axvspan(disturbance_date, recovery_date, color='lightcoral', alpha=0.3, label='Disturbance Phase')
        axz.axvspan(recovery_date, recovery_date + pd.Timedelta(days=30),
                    color='lightgreen', alpha=0.2, label='Recovery Phase')
        axz.text(recovery_date, ytop,
                 f"Recov*: {recovery_date.strftime('%Y-%m-%d')}",
                 color='green', fontsize=9, ha='left', va='top', rotation=90)

    axz.set_title(f"Zoomed: ±100 days | {settlement_id}")
    axz.set_xlabel("Date")
    axz.set_ylabel("NTL Radiance")
    axz.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(settlement_dir, f"BEAST_{settlement_id}_full_cycle_zoom.png"))
    plt.close()

    drop_mag_value = float(drop_mag)
    full_cycle_flag = drop_mag_value < -0.01 and (recovery_cp or slope_recovery > 0.001)
    summary_records.append({
        "Settlement ID": settlement_id,
        "Disturbance Date": disturbance_date.date(),
        "Drop (ΔNTL)": round(drop_mag_value, 4),
        "Recovery CP Date": recovery_cp["date"].date() if recovery_cp else "NA",
        "Recovery Slope": round(slope_recovery, 4) if not pd.isna(slope_recovery) else "NA",
        "Recovery Type": recovery_type,
        "Full Cycle": full_cycle_flag,
        "Disturbance Strength": disturbance_strength
    })

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data_dir", required=True)
    parser.add_argument("-o", "--output_dir", required=True)
    parser.add_argument("-l", "--settlement_list", required=True, help="Path to CSV file with settle_pcod column")
    args = parser.parse_args()

    ntl_file = os.path.join(args.data_dir, "allNTL_allgrid3_props_gaps.csv")
    df_ntl = pd.read_csv(ntl_file)
    df_ntl['YYYY_MM_DD'] = pd.to_datetime(df_ntl['YYYY_MM_DD'])
    df_ntl.set_index('YYYY_MM_DD', inplace=True)
    df_ntl['NTLmean'] = pd.to_numeric(df_ntl['NTLmean'], errors='coerce').fillna(0)

    os.makedirs(args.output_dir, exist_ok=True)
    summary_records = []

    settle_df = pd.read_csv(args.settlement_list)
    settlement_ids = settle_df['settle_pcod'].unique().tolist()

    for sid in settlement_ids:
        print(f"🔄 Processing: {sid}")
        try:
            success = process_settlement(sid, df_ntl, args.output_dir, summary_records)
            if success:
                print(f"✅ Completed: {sid}")
            else:
                print(f"⚠️ Skipped: {sid}")
        except Exception as e:
            print(f"❌ Error in {sid}: {e}")

    pd.DataFrame(summary_records).to_csv(
        os.path.join(args.output_dir, "BEAST_Full_Cycle_Summary_All.csv"), index=False
    )
    print("📄 Summary saved for all processed settlements.")
