import numpy as np
import pandas as pd

"""
Each Method in this class follows the steps given Section 3.2.4 in Ehsan's paper. The paper has not yet been published as of the writing of this code. Contact Adam Rice (adam.w.rice@gmail.com) for the paper and script this was built from.

Lots of the code below was written by Ehsan Kahrizi, but modularized and vetted by Adam Rice

[Table 2]
List of anomaly event type labels. 
1. Anomalies caused by site visits
  - (Code: 1.1 MNT/Class: 1) Maintenance: Routine maintenance by  technicians, causes temporary disruptions in raw data. 
  - (Code: 1.2 CAL/Class: 2) Calibration: Sensor readings are affected during  the calibration process. 
  - (Code: 1.3 LDC/Class: 3) Linear drift correction: Anomalies reflect  retroactive adjustments to earlier data points due Category Code Class Description  to sensor drift that was corrected during a later calibration. 
  - (Code: 1.4 CS/Class: 4) Constant shift: Attributed to errors in sensor setup  or scaling, which technicians later corrected and shifted the raw data. 
2. Other anomalies
  - (Code: 2.1 PF/Class: 5) Power failure: Anomalies caused by interruptions  in the sensor's power supply, causing the sensor and logger package to no longer operate. 
  - (Code: 2.2 SLM/Class: 6) Sensor or logger malfunction: Refers to  malfunctioning hardware issues, where the sensor or data logger fails to operate correctly. 
  - (Code: 2.3 LWL/Class: 7) Low water level: Anomalies where the river's  water level falls below the sensor's installed elevation, which leaves it exposed to air. 
  - (Code: 2.4 VIN/Class: 8) Visual inspection: Anomalies that do not clearly  match any of the above-mentioned categories and require further review or expert judgment.

"""
class AnomalyClassifier:
    def __init__(self, dataManager, verbose=True):
        self.dataManager = dataManager
        self.dataframe = dataManager.get_main()
        self.variable_of_interest = dataManager.settings["Variable"]
        self.cross_variable = dataManager.settings["crossValidateVariable"]
        self.ThrV_1 = dataManager.settings["ThrV_1"]
        self.ThrV_2 = dataManager.settings["ThrV_2"]
        self.ThrV_3 = dataManager.settings["ThrV_3"]
        self.PerThr_3 = dataManager.settings["PerThr_3"]
        self.ThrV_4 = dataManager.settings["ThrV_4"]
        self.n = dataManager.settings["n"]
        self.verbose = verbose
        self._lwl_event_ranges = None

    """
    Master function 
    Processes through the steps in the order they should be done. For more info on each step, look to the comments above each method.
    """
    def process(self):
        if self.verbose: print("\033[92m -- Anomaly Classification -- \033[0m")
        self.identifyEventTypes()
        self.check_cross_variable()
        self.check_ice()
        self.delta_start_end()
        self.check_spCond()
        self.compare_temps()
        self.compare_ave_stage()
        self.ind_5_composite()
        self.maintenance_issues()
        self.sensor_and_logger_malfunctioning()
        self.power_issues()
        self.reading_during_calibration()
        self.post_calibration_CS()
        self.post_calibration_LDC()
        self.final_labeling()
        if self.verbose: print("Done!")

        self.ending_message()

    """
    Anomaly event type labels are added to each data value within an anomaly event in a new column called 'EventType'. We developed a labeling system through data-driven analysis for use in labeling anomaly events according to their type. This categorization approach is designed to perform a workflow to assign the corresponding label, based on patterns discussed in the previous section and logic described in this section. The identified anomaly event types can be categorized into two main categories, each with various subcategories (Table 2). These eight classes constitute an operational taxonomy derived from LRO field and QC procedures, rather than a universally established taxonomy of aquatic sensor anomalies (see Section 5.4).

    First, some anomaly events are associated with site visits by the technicians. These anomaly events are a result of manual interventions, such as maintenance or calibration, performed by technicians during site visits. For example, anomaly events labeled as Maintenance (MNT) indicate when routine maintenance causes temporary disruptions in raw data. Similarly, Calibration (CAL) anomaly events occur when sensor readings are affected during the calibration process. Furthermore, Linear Drift Correction (LDC) anomaly events indicate retroactive adjustments to earlier data points resulting from sensor drift that was corrected during a subsequent calibration. Another subtype of anomaly event associated with site visits, Constant Shift (CS), is attributed to errors in sensor setup or scaling, which technicians later corrected.

    The second category of anomaly event types includes anomaly events originating from sensor infrastructure issues, environmental conditions, or any other conditions that created an anomaly event. Power Failure (PF) anomaly events are caused by interruptions in the sensor's power supply, such as depleted batteries or voltage fluctuations. Further, Sensor/Logger Malfunction (SLM) anomaly events refer to malfunctioning hardware where the sensor or data logger fails to operate correctly. In some cases, anomaly events are due to natural environmental conditions, like Low Water Level (LWL) events, where the river's water level falls below the sensor's installed  elevation, which leaves it exposed to air. Lastly, the Visual Inspection (VIN) label is used when the anomaly event does not clearly match any of the above-mentioned categories and requires further review or expert judgment. The following text outlines the steps, functions, procedures, and logic implemented as a deterministic protocol to set anomaly event type labels for each anomaly event.
    """
    def identifyEventTypes(self):
        if self.verbose: print("Identifying Event Types...")
        df = self.dataframe

        # Step 1: Initialize EventType
        df['EventType'] = ''

        # Step 2: Preserve CorrectionTypeCal values for anomaly type 5
        mask5 = df['_AnomalyType'] == 5
        df.loc[mask5, 'EventType'] = df.loc[mask5, '_CorrectionTypeCal']

        # Step 3: Normalize event marker columns
        df['_StartTimeEvent'] = (df['_StartTimeEvent'].astype(str).str.strip())
        df['_EndTimeEvent'] = (df['_EndTimeEvent'].astype(str).str.strip())

        # Step 4: Track event ranges by integer row position
        event_start_idx = None

        for i, (_, row) in enumerate(df.iterrows()):
            # Detect the start of an event
            if 'Starting time of Event' in row['_StartTimeEvent']: event_start_idx = i

            # Detect the end of an event
            if (event_start_idx is not None and 'Ending time of Event' in row['_EndTimeEvent']):
                event_end_idx = i

                # Assign CAL to anomaly type 4 within this event
                for j in range(event_start_idx, event_end_idx + 1):
                    if df.iloc[j]['_AnomalyType'] == 4:
                        df.iloc[j, df.columns.get_loc('EventType')] = 'CAL'

                # Reset for the next event
                event_start_idx = None

        # Step 5: If an event started but never ended, process to EOF
        if event_start_idx is not None:
            for j in range(event_start_idx, len(df)):
                if df.iloc[j]['_AnomalyType'] == 4:
                    df.iloc[j, df.columns.get_loc('EventType')] = 'CAL'

        # Step 6: Ensure all anomaly type 4 rows are CAL
        df.loc[df['_AnomalyType'] == 4, 'EventType'] = 'CAL'

        # Step 7: Assign OtherType to anomaly types 1, 2, and 3
        mask_other = (df['_AnomalyType'].isin([1, 2, 3]) & (df['EventType'] == ''))
        df.loc[mask_other, 'EventType'] = 'OtherType'

        # Step 8: Preserve CorrectionTypeCal values for anomaly type 5
        df.loc[mask5, 'EventType'] = df.loc[mask5, '_CorrectionTypeCal']

    """
    Second, a new column called 'Ind_3' is calculated to check cross-variable availability. Missing data points can arise from two main causes: 1) a power failure, where all variables are missing for a timestamp, or 2) a sensor/logger malfunction, where only one variable is missing for a timestamp. To distinguish between these, the code assesses data availability using a cross check variable (in the configuration/Settings). For each data row, if the value for the cross check variable is missing at the same timestamp (NaN), 'Ind_3' is set to 1; otherwise, it is set to 0.
    """
    def check_cross_variable(self):
        if self.verbose: print("Checking Cross Variable (Ind_3)")
        # Use the dynamically constructed column in the DataFrame
        self.dataframe['Ind_3'] = np.where(self.dataframe[self.dataManager.settings.settings['crossValidateVariable']].isna(), 1, 0)

    """
    Third, a column called 'Ind_4' is added to our data frame to check for issues related to ice. The code flags potential ice (ICE) events using water temperature. The 'Ind_4' column is set to 1 wherever the raw water temperature is at or below 0 °C, otherwise 'Ind_4' is set to 0. Then, a new column is created called 'Ind_4.1' to filter out the periods that occurred during site visits, because during site visits negative values of water temperature could be due to the sensor being out of the water and are not valid. 'Ind_4.1' refines that signal by marking 1 only when an ice flag occurs outside any sitevisit window (Ind_1 = 0), and 0 otherwise. In short, 'Ind_4' detects freezing conditions, while 'Ind_4.1' isolates freezing conditions that are not artifacts of site visits.
    """
    def check_ice(self):
        if self.verbose: print("Checking Issues with Ice (Ind_4 and Ind_4.1)")
        self.dataframe['Ind_4'] = ''
        self.dataframe['Ind_4'] = np.where(self.dataframe["WaterTemp_EXO"] <= 0, 1, 0)

        self.dataframe['Ind_4.1'] = None
        self.dataframe['Ind_4.1'] = np.where((self.dataframe['Ind_4'] == 1) & (self.dataframe['_FieldNoteFlag'] == 0), 1, 0)
    
    """
    Fourth, the code checks for issues related to sensor exposure to air. This code uses an 'LWL' flag to identify when the sensor is exposed to air. Four different conditions are checked to verify that a sensor is out of the water and exposed to air or not. 
      * Checking conditions such as sharp changes in values of specific conductance, comparing air temperature with water temperature, and examining the stage of water can help identify when the sensor is not submerged in the water. A new column called 'Ind_5.1' is created to check the drop changes at the beginning and end of each anomaly event, indicating that the surrounding sensor condition changed. 'Ind_5.1' checks each non-calibration event window and fills all rows for events with a value of 1 if both the start- and end-boundary jumps in the raw data series exceed a threshold, 'ThrV_1'. Otherwise 'Ind_5.1' is set to 0 (Figure 4). 'ThrV_1' is a predefined threshold that is defined in the settings for the object.
    """
    def delta_start_end(self):
        if self.verbose: print("Delta Start/End (Ind_5.1)...")
        # Reset index and standardize column names
        self.dataframe.reset_index(inplace=True)
        self.dataframe.columns = self.dataframe.columns.str.strip()
        self.dataframe['LocalDateTime'] = pd.to_datetime(self.dataframe['LocalDateTime'], errors='coerce')
        self.dataframe['delta_Start'] = None
        self.dataframe['delta_End'] = None
        self.dataframe['Ind_5.1'] = None
        missing_data_flag = "NoData"

        ranges = self.get_lwl_event_ranges()

        for k, (start_idx, end_idx, event_idx) in ranges.items():
            # Skip calibration (_AnomalyType = 4) and calibration-affected (Ind_2 = 5) events
            if self.dataframe.at[event_idx[0], '_AnomalyType'] in [4, 5]:
                continue

            event_datetimes = self.dataframe.loc[event_idx, 'LocalDateTime']
            standard_event_idx = event_datetimes.index[event_datetimes.dt.minute % 15 == 0]
            if len(standard_event_idx) == 0:
                continue

            # `delta_Start`: jump from the last normal point before the event to the first point of the event
            start_val = self.dataframe.at[start_idx, self.variable_of_interest]
            first_val = self.dataframe.at[standard_event_idx[0], self.variable_of_interest]
            delta_start = abs(start_val - first_val) if pd.notnull(start_val) and pd.notnull(first_val) else missing_data_flag

            # `delta_End`: jump from the last point of the event to the first normal point after the event
            end_val = self.dataframe.at[end_idx, self.variable_of_interest]
            last_val = self.dataframe.at[standard_event_idx[-1], self.variable_of_interest]

            delta_end = abs(end_val - last_val) if pd.notnull(end_val) and pd.notnull(last_val) else missing_data_flag

            self.dataframe.at[start_idx, 'delta_Start'] = delta_start
            self.dataframe.at[end_idx, 'delta_End'] = delta_end

            # Part B: `Ind_5.1` = 1 when the value jumps both when entering and leaving the event
            if delta_start != missing_data_flag and delta_end != missing_data_flag:
                self.dataframe.loc[event_idx, 'Ind_5.1'] = 1 if (delta_start > self.ThrV_1 and delta_end > self.ThrV_1) else 0

        return self.dataframe

    """
      * A new column called 'Ind_5.2' is then created to check the specific conductance of water, as conductivity measured by the specific conductance sensor is dramatically reduced when the sensor is exposed to air. The 'Ind_5.2' column is filled with a value of 1 on timesteps outside calibration windows when specific conductance is missing or below a set threshold, 'ThrV_2'. 'ThrV_2' is a predefined threshold that is defined in the 'Initial_Settings.yaml' file. 
    """
    def check_spCond(self):
        if self.verbose: print("Checking Specific Conductance (Ind_5.2)...")
        # Initialize 'Ind_5.2' with None
        self.dataframe['Ind_5.2'] = None

        # Apply the condition only for rows where 'Ind_2' is NOT 4 or 5 and 'TimeInterval' is 'Standard'
        self.dataframe['Ind_5.2'] = np.where(
            (~self.dataframe['_AnomalyType'].isin([4, 5])) &  # Exclude rows with Ind_2 == 4 or 5
            (self.dataframe['TimeInterval'] == 'Standard') &  # Apply only to 'Standard' intervals
            ((self.dataframe['SpCond'].isna()) | (self.dataframe['SpCond'] < self.ThrV_2)), 
            1,  # Set 'Ind_5.2' to 1 if the condition is met
            0   # Otherwise, set 'Ind_5.2' to 0
        )

    """
      * Then, a new column called 'Ind_5.3' is created to compare the average water temperature and air temperature for each anomaly event period. The 'Ind_5.3' column is filled with 1 when the average absolute difference between water and air temperature (|Water Temperature - Air Temperature|) over the event is small (below 'ThrV_3' set in the 'Initial_Settings.yaml' file), suggesting the aquatic sensor is exposed to air. 
    """
    def compare_temps(self):
        if self.verbose: print("Checking Water and Air Temperatures (Ind_5.3)...")
        # Absolute calculation
        self.dataframe['delta_Water_DataSetClimate'] = abs(self.dataframe['WaterTemp_EXO'] - self.dataframe['AirTemp_EE08_avg'])
        self.dataframe['delta_Water_DataSetClimate_avg'] = None
        self.dataframe['Ind_5.3'] = None

        # `Ind_5.3` = 1 when, on average over the event, water temperature is close to air temperature
        for k, (start_idx, end_idx, event_idx) in self.get_lwl_event_ranges().items():
            # Skip calibration (Ind_2 = 4) and calibration-affected (Ind_2 = 5) events
            if self.dataframe.at[event_idx[0], '_AnomalyType'] in [4, 5]:
                continue
            event_rows = self.dataframe.loc[event_idx]
            valid_deltas = event_rows.loc[
                (event_rows['TimeInterval'] == 'Standard') &
                (pd.notnull(event_rows['delta_Water_DataSetClimate']))
            ]['delta_Water_DataSetClimate']

            if not valid_deltas.empty:
                avg_delta = valid_deltas.mean()
                self.dataframe.loc[event_idx, 'delta_Water_DataSetClimate_avg'] = avg_delta
                self.dataframe.loc[event_idx, 'Ind_5.3'] = 1 if avg_delta < self.ThrV_3 else 0

    """
      * A column called 'Ind_5.4' is then created in the data frame to compare the average water stage within a buffer of time before and after the anomaly event, and to compare the difference with the average water stage during the anomaly event. The code calculates the n-point averages before and after the event (Figure 5). If both are greater than a threshold 'ThrV_4', it indicates that the water level is reduced and the sensor may be exposed to air. In this case, the 'Ind_5.4' column is filled with 1; otherwise, 0. The 'n' and 'ThrV_4' are predefined thresholds that are defined in the 'Initial_Settings.yaml' file. 
    """
    def compare_ave_stage(self):
        if self.verbose: print("Checking Average Stage (Ind_5.4)...")
        # Initialize columns with None
        self.dataframe['Stage_avg'] = None
        self.dataframe['Stage_backward'] = None
        self.dataframe['Stage_forward'] = None
        self.dataframe['delta_Stage_Backward'] = None
        self.dataframe['delta_Stage_Forward'] = None
        self.dataframe['Ind_5.4'] = None

        def mean_standard_stage(rows):
            """Average Stage_QC0 over the Standard rows that have a value (None if there are none)."""
            values = rows.loc[(rows['TimeInterval'] == 'Standard') & pd.notnull(rows['Stage']), 'Stage']
            return values.mean() if not values.empty else None

        # `Ind_5.4` = 1 when the stage during the event differs from the stage both before and after the event
        for k, (start_idx, end_idx, event_idx) in self.get_lwl_event_ranges().items():
            # Average Stage over the event range (including the normal points that bound it)
            event_range = self.dataframe.loc[start_idx:end_idx]
            valid_stage_values = event_range.loc[pd.notnull(event_range['Stage']), 'Stage']
            avg_stage = valid_stage_values.mean() if not valid_stage_values.empty else None

            # Average over the `n` rows before and after the event
            avg_backward_stage = mean_standard_stage(self.dataframe.loc[max(0, start_idx - self.n):start_idx - 1])
            avg_forward_stage = mean_standard_stage(self.dataframe.loc[end_idx + 1:end_idx + self.n])

            self.dataframe.loc[event_idx, 'Stage_avg'] = avg_stage
            self.dataframe.loc[event_idx, 'Stage_backward'] = avg_backward_stage
            self.dataframe.loc[event_idx, 'Stage_forward'] = avg_forward_stage

            # Calculate deltas and `Ind_5.4` only if all required values are available
            if pd.notnull(avg_stage) and pd.notnull(avg_backward_stage) and pd.notnull(avg_forward_stage):
                delta_stage_backward = abs(avg_backward_stage - avg_stage)
                delta_stage_forward = abs(avg_forward_stage - avg_stage)
                self.dataframe.loc[event_idx, 'delta_Stage_Backward'] = delta_stage_backward
                self.dataframe.loc[event_idx, 'delta_Stage_Forward'] = delta_stage_forward
                self.dataframe.loc[event_idx, 'Ind_5.4'] = 1 if (delta_stage_forward > self.ThrV_4 and delta_stage_backward > self.ThrV_4) else 0
    
    """
      * Finally, a new column called 'Ind_5' is created to composite the prior logic. The 'Ind_5' column is set to 1 only if 'Ind_5.4' = 1 and at least one of 'Ind_5.1'/ 'Ind_5.2' / 'Ind_5.3' = 1 (else 0, or None if prerequisites are missing), yielding a robust out of water indicator.
    """
    def ind_5_composite(self):
        if self.verbose: print("Compositing Ind_5's together...")
        self.dataframe['Ind_5'] = None

        # Loop through the dataframe and apply the logic for 'Ind_5'
        for i, row in self.dataframe.iterrows():
            # Ensure that Ind_5.1, Ind_5.2, Ind_5.3, and Ind_5.4 are not null
            if pd.notnull(row['Ind_5.1']) and pd.notnull(row['Ind_5.2']) and pd.notnull(row['Ind_5.3']) and pd.notnull(row['Ind_5.4']):
                # Check the condition for Ind_5.4 (mandatory requirement) and one of Ind_5.1, Ind_5.2, or Ind_5.3
                if row['Ind_5.4'] == 1 and (row['Ind_5.1'] == 1 or row['Ind_5.2'] == 1 or row['Ind_5.3'] == 1):
                    self.dataframe.at[i, 'Ind_5'] = 1  # Set 'Ind_5' to 1 if the conditions are met
                else:
                    self.dataframe.at[i, 'Ind_5'] = 0  # Set 'Ind_5' to 0 if conditions are not met
            else:
                self.dataframe.at[i, 'Ind_5'] = None  # Leave 'Ind_5' as None if any required indicator is missing

    """
    As a fifth step, a column called 'Ind_6' is added to the data frame to check for issues related to maintenance. The code uses this column to flag maintenance-related site visits that are not calibrations. Specifically, it sets 'Ind_6 = 1' whenever '_FieldNoteFlag = 1' (i.e., a regular site visit window is present) and 'Ind_6 = 0' otherwise. This cleanly separates routine maintenance/inspection periods from calibration events, helping capture times when technicians were on site and non-calibration activities could affect sensor readings.
    """
    """ Sooo.... you're literally just setting Ind_6 to be the same as _FieldNoteFlag?? This makes no sense at all... """
    def maintenance_issues(self):
        if self.verbose: print("Checking Maintenance Issues (Ind_6)...")
        self.dataframe['Ind_6'] = np.where((self.dataframe['_FieldNoteFlag'] == 1), 1, 0)

    """
    Sixth, the code adds column 'Ind_7' to the data frame to check for issues related to sensor and logger malfunctioning. It flags events that appear to be sensor errors and that are not caused by site visits or missing values. The code sets 'Ind_7 = 1' when an anomaly event is present ('Ind_2 ∈ {1, 2}'), it occurs outside any site-visit window ('Ind_1 = 0'), and the chosen cross validation variable is available ('Ind_3 = 0'), which helps confirm that the issue is with the specific variable being processed. Otherwise, 'Ind_7 = 0'.
    """
    def sensor_and_logger_malfunctioning(self):
        if self.verbose: print("Checking Sensor and Logger Malfunctions (Ind_7)...")
        self.dataframe['Ind_7'] = None
        self.dataframe['Ind_7'] = np.where(
            ((self.dataframe['_AnomalyType'] == 1) | (self.dataframe['_AnomalyType'] == 2)) & 
            (self.dataframe['_FieldNoteFlag'] == 0) & 
            (self.dataframe['Ind_3'] == 0), 1, 0)

    """
    Seventh, a new column 'Ind_8' is added to the data frame to check for issues related to power. The code flags anomaly events that occur outside site visits, but where data for the supporting cross validation variable is also missing. Specifically, the code sets 'Ind_8 = 1' when an event is detected ('_AnomalyType ∈ {1, 2}'), there is no site-visit influence ('_FieldNoteFlag = 0'), and the cross validation variable is unavailable ('Ind_3 = 1'). Otherwise, the code assigns 'Ind_8 = 0'. This distinguishes anomaly events caused by potential sensor/logger malfunctions from those caused by power failure.
    """
    def power_issues(self):
        if self.verbose: print("Checking Power Related Issues (Ind_8)...")
        self.dataframe['Ind_8'] = None

        # Logic:
        self.dataframe['Ind_8'] = np.where(
            ((self.dataframe['_AnomalyType'] == 1) | (self.dataframe['_AnomalyType'] == 2)) & 
            (self.dataframe['_FieldNoteFlag'] == 0) & 
            (self.dataframe['Ind_3'] == 1), 1, 0)

    """
    Eighth, the column 'Ind_10' is added to the data frame to help check for events that occur during a calibration. The code identifies rows that occur during a calibration event for all variables except water temperature. It simply sets 'Ind_10 = 1' wherever '_AnomalyType = 4' (denoting calibration-visit periods) and 0 otherwise, allowing for quick isolation of data collected during calibration.
    """
    def reading_during_calibration(self):
        if self.variable_of_interest == 'WaterTemp_EXO': return
        if self.verbose: print("Checking Readings During Calibration (Ind_10)...")

        # Initialize 'Ind_10' column with None
        self.dataframe['Ind_10'] = None

        # Loop through the dataframe and apply the logic for 'Ind_10'
        for i, row in self.dataframe.iterrows():
            # Ensure that _AnomalyType is not null
            if pd.notnull(row['_AnomalyType']):
                if row['_AnomalyType'] == 4:
                    self.dataframe.at[i, 'Ind_10'] = 1 
            else:
                self.dataframe.at[i, 'Ind_10'] = None

    """
    Ninth, the column 'Ind_11' is added to the dataframe to check for anomaly events that had a post-calibration, constant shift. The code flags rows that are classified as post-calibration constant shift (for all variables except water temperature). The code sets 'Ind_11' = 1 wherever the column '_CorrectionTypeCal' = 'CS' for constant shift (i.e., the raw data - manually corrected data difference is nonzero but constant) otherwise 0. This makes it easy to isolate data values within periods where a fixed bias likely remained after calibration.
    """
    def post_calibration_CS(self):
        if self.variable_of_interest == 'WaterTemp_EXO': return
        if self.verbose: print("Checking Anomaly Events with Post-Calibration, Constant Shift (Ind_11)...")

        # Initialize 'Ind_11' column with None
        self.dataframe['Ind_11'] = None

        # Loop through the dataframe and apply the logic for 'Ind_11'
        for i, row in self.dataframe.iterrows():
            # Ensure that '_CorrectionTypeCal' is not null
            if pd.notnull(row['_CorrectionTypeCal']):
                if row['_CorrectionTypeCal'] == 'CS':
                    self.dataframe.at[i, 'Ind_11'] = 1 
            else:
                self.dataframe.at[i, 'Ind_11'] = None  

    """
    As a tenth step, the final indicator column, 'Ind_12', is used to check for anomaly events that had a post-calibration, linear drift correction shift. This indicator flags all rows where a linear drift correction was applied to non-water temperature variables. Specifically, for every row, if the column '_CorrectionTypeCal' = 'LDC' for linear drift correction and the variable is not temperature, then 'Ind_12' is set to 1; otherwise, it is set to 0. This helps isolate and track instances where a linear drift adjustment was used during calibration or post-processing, enabling clearer auditing of corrections across variables.
    """
    def post_calibration_LDC(self):
        if self.variable_of_interest == 'WaterTemp_EXO': return

        self.dataframe['Ind_12'] = None
        # Loop through the dataframe and apply the logic for 'Ind_12'
        for i, row in self.dataframe.iterrows():
            # Ensure that `CorrectionTypeCal` is not null
            if pd.notnull(row['_CorrectionTypeCal']):
                if row['_CorrectionTypeCal'] == 'LDC':
                    self.dataframe.at[i, 'Ind_12'] = 1 
            else:
                self.dataframe.at[i, 'Ind_12'] = None

    """
    In the final step, the final label and class are mapped to the dataset. The final event type label accumulates all the previous indicators and steps to assign an event type to each anomaly event. Firstly, the columns named 'Label' and 'Class' are created in our data frame. Then the code assigns a single, final event label to each timestamp by evaluating a prioritized set of indicators. For water temperature, calibration-related logic is omitted. Labels are applied in the order: 'MNT' if a non-calibration site visit is active ('Ind_6=1'), 'PF' if an anomaly coincides with missing cross validation variable data ('Ind_8=1'), 'SLM' if an anomaly occurs with the cross validation variable present ('Ind_7=1'), and 'LWL' if the low-water level composite flag is triggered ('Ind_5=1'); otherwise 'VIN' (meaning that none of the mentioned labels can represent this anomaly event, and it needs visual inspection for further assessment). For other variables, calibration states are prioritized first ('CAL' during calibration ('Ind_10=1'), 'CS' ('Ind_11=1'), and 'LDC' ('Ind_12=1')) followed by 'MNT', 'PF', 'SLM', and 'LWL' as above. Rows that fall within 'Ind_2'∈{1..5} but match none of the higher-priority rules default to 'VIN', while rows outside that set remain unlabeled. Labels are finally mapped to numeric classes ('MNT=1', 'CAL=2', 'LDC=3', 'CS=4', 'PF=5', 'SLM=6', 'LWL=7', 'VIN=8') for convenience in downstream analysis and storage.
    """
    def final_labeling(self):
        if self.verbose: print("Assembling Final Labeling...")
        conditions, labels = None, None
        if self.variable_of_interest == "WaterTemp_EXO":
            conditions = [
                (self.dataframe['Ind_6'] == 1), # MNT
                (self.dataframe['Ind_8'] == 1), # PF
                (self.dataframe['Ind_7'] == 1), # SLM
                (self.dataframe['Ind_5'] == 1)  # LWL
            ]
            labels = ['MNT', 'PF', 'SLM', 'LWL']
        else:
            conditions = [
                (self.dataframe['Ind_10'] == 1), # CAL
                (self.dataframe['Ind_11'] == 1), # CS
                (self.dataframe['Ind_12'] == 1), # LDC
                (self.dataframe['Ind_6'] == 1),  # MNT 
                (self.dataframe['Ind_8'] == 1),  # PF 
                (self.dataframe['Ind_7'] == 1),  # SLM
                (self.dataframe['Ind_5'] == 1),  # LWL
            ]
            labels = ['CAL', 'CS', 'LDC', 'MNT', 'PF', 'SLM', 'LWL']

        # Apply labels based on conditions
        self.dataframe['Label'] = np.where(
            self.dataframe['_AnomalyType'].isin([1, 2, 3, 4, 5]), 
            np.select(conditions, labels, default='VIN'), 
            None
        )

        # Map the labels to class numbers
        self.dataframe['class'] = np.select(
            [self.dataframe['Label'] == label for label in ['MNT', 'CAL', 'LDC', 'CS', 'PF', 'SLM', 'LWL', 'VIN']],
            [1, 2, 3, 4, 5, 6, 7, 8]
        )


    ### Helper Functions ###
    """
    This method is called for use on Ind_5

    Ehsan's Comments on this function:
        Map each event number k to (start_idx, end_idx, event_idx):
        start_idx: row holding 'Starting time of Event k' (the Standard row just before the event)
        end_idx:   row holding 'Ending time of Event k' (the Standard row just after the event)
        event_idx: rows that belong to event k (Event_Counter == k)
    Events are matched by number (not by scanning for the next start/end marker), because the markers of adjacent events interleave, and because the marker rows themselves are normal rows that must not be filtered out.
    """
    def get_lwl_event_ranges(self):
        if self._lwl_event_ranges != None: return self._lwl_event_ranges

        if self.variable_of_interest == 'WaterTemp_EXO': start_column, end_column= '_StartTimeEvent', '_EndTimeEvent'
        else: start_column, end_column = '_OtherStartTime', '_OtherEndTime'

        starts = self.dataframe[start_column].astype(str).str.extract(r'Starting time of Event (\d+)', expand=False).dropna().astype(int)
        ends = self.dataframe[end_column].astype(str).str.extract(r'Ending time of Event (\d+)', expand=False).dropna().astype(int)
        start_map = {k: idx for idx, k in starts.items()}
        end_map = {k: idx for idx, k in ends.items()}
        counter = pd.to_numeric(self.dataframe['_AnomalyEventNumber'], errors='coerce')

        ranges = {}
        for k in sorted(set(start_map) & set(end_map)):
            event_idx = self.dataframe.index[counter == k]
            if len(event_idx) > 0:
                ranges[k] = (start_map[k], end_map[k], event_idx)
        return ranges

    """
    Prints a simplified version of the final output (if verbose)
    """
    def ending_message(self):
        if not self.verbose: return
        print("\n\033[92m -- Label Distribution -- \033[0m")
        print(self.dataframe['Label'].value_counts())
        print()
