# BEAST_Driver
This Python script analyzes nighttime light (NTL) data to detect disturbances in human settlements, particularly in response to cyclone events, using the BEAST model. The script identifies disturbances, assesses recovery, and applies statistical methods (t-tests and Cohen's d) to confirm significance and effect size.

Below is a list of **all the variables** that are chosen, decided, or selected at different stages in the code:

### 1. **User-defined Variables (via Command-Line Arguments)**

These variables are selected when the script is executed with command-line arguments:

* **`data_dir`**: Directory containing the input data file (`allNTL_allgrid3_props_gaps.csv`).
* **`output_dir`**: Directory where output files will be saved.
* **`settlement_list`**: Path to the CSV file containing settlement IDs (settle\_pcod).

### 2. **Data Variables**

These variables are derived or loaded from the input files:

* **`ntl_file`**: Path to the file containing the NTL data.
* **`df_ntl`**: DataFrame that holds all the NTL data.

  * Columns:

    * **`YYYY_MM_DD`**: The date (timestamp) for the NTL data.
    * **`NTLmean`**: The mean NTL radiance for each timestamp.
* **`settle_df`**: DataFrame that holds the list of settlement IDs (from the settlement list CSV).
* **`settlement_ids`**: List of unique settlement IDs (`settle_pcod` column from the `settle_df`).

### 3. **Processed Settlement Variables**

These variables are specific to each settlement being processed:

* **`settlement_id`**: The unique ID for each settlement (from the list of settlements).
* **`its_data`**: DataFrame containing the subset of NTL data for the current settlement.

  * Contains the same columns (`YYYY_MM_DD`, `NTLmean`) plus derived columns:

    * **`NTLmean`**: Outlier-removed NTL mean values.
    * **`BEAST_Trend`**: Trend values calculated by the BEAST model.
    * **`Deviation`**: The difference between `NTLmean` and `BEAST_Trend`.
* **`disturbance_strength`**: A variable initialized as `"none"`, which is not explicitly updated in the code but could be used to categorize the strength of the disturbance based on `drop_mag`.

### 4. **Cyclone and BEAST Variables**

These variables are derived from the BEAST model and cyclone date:

* **`known_cyclone_date`**: The predefined cyclone date (`2022-02-05`).
* **`cps`**: The change points detected by the BEAST model.
* **`trend_values`**: The trend values of the NTL data, calculated by the BEAST model.
* **`cp_dates`**: The corresponding dates for each change point in `cps`.
* **`valid_cp_indices`**: List of valid change points that are within ±60 days of the `known_cyclone_date`.
* **`disturbance_idx`**: The index of the valid disturbance change point in the `cps`.
* **`drop_mag`**: The magnitude of the disturbance, calculated as the difference between the trend values before and after the disturbance.
* **`disturbance_date`**: The date of the disturbance (corresponding to `disturbance_idx`).

### 5. **t-test Variables**

These variables are used for performing the t-test to check for statistical significance:

* **`pre_dev`**: The deviation (difference between `NTLmean` and `BEAST_Trend`) values before the disturbance date.
* **`post_dev`**: The deviation values after the disturbance date.
* **`t_stat`**: The t-statistic calculated by the t-test.
* **`p_value`**: The p-value from the t-test.

### 6. **Recovery Detection Variables**

These variables help in detecting the recovery phase after a disturbance:

* **`recovery_cp`**: The change point indicating recovery, including:

  * **`idx`**: The index of the recovery change point.
  * **`date`**: The date of the recovery change point.
  * **`drop`**: The change in trend at the recovery change point.
* **`recovery_cp_date`**: The date of the recovery change point, or `"NA"` if no recovery is found.
* **`slope_recovery`**: The calculated slope of the recovery, defined as the change in trend over a defined recovery window.
* **`recovery_type`**: The type of recovery, either `"CP"`, `"slope"`, or `"none"`.

### 7. **Output Variables**

These variables store and save the final output:

* **`settlement_dir`**: The directory for the specific settlement's output files.
* **`summary_records`**: List of dictionaries holding summary information for each settlement.

  * Contains keys like:

    * **`Settlement ID`**: The settlement ID.
    * **`Disturbance Date`**: The disturbance date.
    * **`Drop (ΔNTL)`**: The magnitude of the disturbance (`drop_mag`).
    * **`Recovery CP Date`**: The recovery change point date, or `"NA"` if no recovery was detected.
    * **`Recovery Slope`**: The recovery slope, or `"NA"` if no recovery was detected.
    * **`Recovery Type`**: The recovery type (`"CP"`, `"slope"`, or `"none"`).
    * **`Full Cycle`**: Boolean indicating if the settlement experienced a full recovery cycle.
    * **`Disturbance Strength`**: The strength of the disturbance (`disturbance_strength`).

### 8. **Cohen's d Calculation Variables**

These variables are used for calculating Cohen's d:

* **`before`**: The values of the deviations before the disturbance (same as `pre_dev`).
* **`after`**: The values of the deviations after the disturbance (same as `post_dev`).
* **`d`**: The calculated Cohen's d, representing the effect size.

### 9. **Plotting Variables**

These variables are used for creating and saving plots:

* **`zoom_window`**: The number of days before and after the disturbance to zoom in on for the plot.
* **`zoom_data`**: The subset of the data within the ±100 days window around the disturbance date.
* **`fig`** and **`axz`**: The figure and axes for plotting the zoomed-in plot.
* **`ytop`**: The y-axis upper limit used for positioning text annotations in the plot.

---

### Summary of Key Variables:

* **Settlement Variables**: `settlement_id`, `its_data`, `disturbance_date`, `drop_mag`, etc.
* **Cyclone & BEAST Variables**: `known_cyclone_date`, `cps`, `disturbance_idx`, `trend_values`, etc.
* **Statistical Variables**: `pre_dev`, `post_dev`, `t_stat`, `p_value`, etc.
* **Recovery Variables**: `recovery_cp`, `recovery_cp_date`, `slope_recovery`, etc.
* **Output Variables**: `settlement_dir`, `summary_records`, etc.
* **Cohen's d Variables**: `before`, `after`, `d`.
* **Plotting Variables**: `zoom_window`, `zoom_data`, `fig`, `axz`, `ytop`, etc.

These are all the variables that are either explicitly defined or chosen at some point in the script. Each plays a role in detecting disturbances, calculating statistical measures, and generating plots.
