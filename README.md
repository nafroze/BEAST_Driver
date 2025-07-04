# BEAST\_Driver

This Python script analyzes nighttime light (NTL) data to detect disturbances in human settlements, particularly in response to cyclone events, using the BEAST model. The script identifies significant negative changes in NTL values (interpreted as disturbances), evaluates statistical confidence, and optionally plots recovery phases.

## 🔧 What the Script Does

- Filters and processes NTL time series per settlement.
- Runs the RBeast algorithm to detect change points.
- Filters change points that fall within ±60 days of a known cyclone date.
- Applies statistical tests (t-test, Cohen's d) to assess change significance.
- Detects recovery (if any) and classifies the recovery type.
- Saves change points, raw and trend time series, and summary metrics.
- Generates two plots:
  - Full-range plot (with cyclone and disturbance dates marked)
  - Zoomed-in plot (±60 days around the cyclone date)

## 🚀 Command-Line Arguments

The script is designed to be executed from a command line or SLURM environment:

```bash
python3 beast_driver.py \
  -d <path_to_data_dir> \
  -o <path_to_output_dir> \
  -l <settlement_list.csv> \
  -c <cyclone_date YYYY-MM-DD>
```

## 📂 File Structure

- `allNTL_allgrid3_props_gaps.csv`: Main input file with time series NTL data.
- `BATSIRAI_settle.csv`: CSV file listing `settle_pcod` IDs to analyze.
- `BEAST_OUTPUT/`: Output folder where all CSVs and plots will be saved.

## 🔢 Variables and Data Flow

### 1. **User-defined Variables (via CLI)**

- `data_dir`: Folder with input CSV files.
- `output_dir`: Folder for saving results.
- `settlement_list`: CSV with list of settlement IDs (`settle_pcod`).
- `cyclone_date`: Known cyclone event date (e.g. 2022-02-05).

### 2. **Data Variables**

- `df_ntl`: DataFrame from `allNTL_allgrid3_props_gaps.csv`.

  - Columns:
    - `YYYY_MM_DD`: Date
    - `NTLmean`: Mean radiance
    - `settl_pcod`: Settlement code

- `settle_df`: DataFrame from settlement list CSV

  - Column: `settle_pcod`

### 3. **Per-Settlement Variables**

- `its_data`: Subset of df\_ntl for each settlement
- `NTLmean`: Outlier-filtered radiance
- `BEAST_Trend`: Output trend from BEAST
- `Deviation`: NTLmean - BEAST trend
- `settlement_id`: Unique settlement code

### 4. **Cyclone & BEAST Analysis**

- `known_cyclone_date`: Cyclone event date
- `cps`: Change point indices (from BEAST)
- `trend_values`: Trend values per date
- `cp_dates`: Change point dates
- `valid_cp_indices`: Subset within ±60 days of cyclone date
- `drop_mag`: Drop magnitude at each CP

### 5. **Statistical Testing**

- `pre_dev`, `post_dev`: Deviation values before/after CP
- `t_stat`, `p_val`: From t-test
- `cohen_d`: Effect size (Cohen's d)

### 6. **Recovery Detection**

- `recovery_cp`: Index of recovery CP
- `recovery_cp_date`: Recovery CP date
- `slope_recovery`: Recovery slope
- `recovery_type`: "CP", "slope", or "none"

### 7. **Output Variables**

- `summary_records`: List of results (one per settlement)
- CSVs per settlement: BEAST trends, change points
- PNG plots (full and zoomed)

### 8. **Plotting Variables**

- `zoom_window`: 60 days (before/after cyclone)
- `zoom_data`: NTL subset within zoom window
- `ytop`: Used for annotations

---

## 🖼️ Output Examples

Each valid settlement produces:

- `BEAST_<settlement>.png`: Full-range plot
- `BEAST_<settlement>_zoomed.png`: ±60 days plot
- `BEAST_<settlement>.csv`: Time series with trend
- `BEAST_<settlement>_changepoints.csv`: CP index and probability
- `BEAST_Summary_All.csv`: Summary metrics for all settlements

---

## ⚙️ SLURM / HPC Usage

### Submit Single Settlement:

```bash
make Beast_slurm SETTLEMENT_ID=MG1234567890
```

### Submit Batch Processing:

```bash
make Beast_batch_slurm CYCLONE_DATE=2022-02-05
```

Ensure Makefile has correct paths and environment configurations.

---

## 🧠 Notes

- Cyclone-aware filtering ensures only disturbances close to the event are visualized.
- Script skips settlements with insufficient data or low brightness.
- Only settlements with negative CPs within ±60 days are analyzed.

---

## 🧪 Dependencies

- Python 3.7+
- Rbeast
- pandas, numpy, matplotlib, sklearn, scipy

---

## 🧑‍💻 Author

- Maintained by: afrozen ([afrozen@oregonstate.edu](mailto\:afrozen@oregonstate.edu))
- Institution: CEOAS, Oregon State University

