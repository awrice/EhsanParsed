import numpy as np
import pandas as pd

"""
Each Method in this class follows the steps given Section 3.2.4 in Ehsan's paper. The paper has not yet been published as of the writing of this code. Contact Adam Rice (adam.w.rice@gmail.com) for the paper and script this was built from.

Lots of the code below was written by Ehsan Kahrizi, but modularized and vetted by Adam Rice

Table 2 List of anomaly event type labels. 
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


I have changed the names of the columns from the original paper (because the original names were confusing). Preceeding underscores have been added to the names to denote these are analysis columns, not data columns. The key is given below:
    - EventType -> EventType

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
    Master function processes through the steps in the order they should be done. For more info on each step, look to the comments above each method.
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
        if self.verbose: print("Done!")

    """
    """
    def _identifyEventTypes(self):
        # Step 1: Create a new column 'EventType' initialized as an empty string
        self.dataframe['EventType'] = ''

        # Step 2: Assign 'EventType' where '_AnomalyType' == 5 (Keep CorrectionTypeCal values)
        self.dataframe.loc[self.dataframe['_AnomalyType'] == 5, 'EventType'] = self.dataframe.loc[self.dataframe['_AnomalyType'] == 5, '_CorrectionTypeCal']

        # Ensure '_StartTimeEvent' and '_EndTimeEvent' are properly formatted
        self.dataframe['_StartTimeEvent'] = self.dataframe['_StartTimeEvent'].astype(str).str.strip()
        self.dataframe['_EndTimeEvent'] = self.dataframe['_EndTimeEvent'].astype(str).str.strip()

        # Step 3: Identify event ranges and assign 'CAL' for '_AnomalyType = 4'
        event_start_idx = None
        event_end_idx = None

        for i, row in self.dataframe.iterrows():
            # Identify the start of an event
            if isinstance(row['_StartTimeEvent'], str) and 'Starting time of Event' in row['_StartTimeEvent']:
                event_start_idx = i  # Store the start index

            # Identify the end of the event
            if isinstance(row['_EndTimeEvent'], str) and 'Ending time of Event' in row['_EndTimeEvent']:
                event_end_idx = i  # Store the end index

            # If an event start is detected but no explicit end, use the last row in the event
            if event_start_idx is not None:
                if event_end_idx is None:
                    event_end_idx = i  # Use the last detected row if no explicit end is found

                # Apply event type assignment for the detected range
                print(event_start_idx, event_end_idx)

                for j in range(event_start_idx, event_end_idx + 1):
                    anomaly_type_value = self.dataframe.at[j, '_AnomalyType']
                    if anomaly_type_value == 4:
                        self.dataframe.at[j, 'EventType'] = 'CAL'

                # Reset tracking for the next event *only if* an event fully processed
                if event_end_idx is not None:
                    event_start_idx = None
                    event_end_idx = None

        # Step 4: Ensure 'CAL' is assigned before 'OtherType' --------------------------------------------------
        self.dataframe.loc[self.dataframe['_AnomalyType'] == 4, 'EventType'] = 'CAL'

        # Step 5: Ensure ALL `_AnomalyType = 3, 2, 1` values are assigned `OtherType`, even if they were missed -------
        self.dataframe.loc[(self.dataframe['_AnomalyType'].isin([1, 2, 3])) & (self.dataframe['EventType'] == ''), 'EventType'] = 'OtherType'

        # Step 6: Ensure 'CorrectionTypeCal' values remain unchanged where _AnomalyType = 5 ---------------------------
        self.dataframe.loc[self.dataframe['_AnomalyType'] == 5, 'EventType'] = self.dataframe['CorrectionTypeCal']
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
    Section 3.2.4 - Step 2
    Second, a new column called 'Ind_3' is calculated to check cross-variable availability. Missing data points can arise from two main causes: 1) a power failure, where all variables are missing for a timestamp, or 2) a sensor/logger malfunction, where only one variable is missing for a timestamp. To distinguish between these, the code assesses data availability using a cross check variable (in the configuration/Settings). For each data row, if the value for the cross check variable is missing at the same timestamp (NaN), 'Ind_3' is set to 1; otherwise, it is set to 0.
    """
    def check_cross_variable(self):
        if self.verbose: print("Checking Cross Variable (Ind_3)")
        # Use the dynamically constructed column in the DataFrame
        self.dataframe['Ind_3'] = np.where(self.dataframe[self.dataManager.settings.settings['crossValidateVariable']].isna(), 1, 0)

    """
    Section 3.2.4 - Step 3
    Third, a column called 'Ind_4' is added to our data frame to check for issues related to ice. The code flags potential ice (ICE) events using water temperature. The 'Ind_4' column is set to 1 wherever the raw water temperature is at or below 0 °C, otherwise 'Ind_4' is set to 0. Then, a new column is created called 'Ind_4.1' to filter out the periods that occurred during site visits, because during site visits negative values of water temperature could be due to the sensor being out of the water and are not valid. 'Ind_4.1' refines that signal by marking 1 only when an ice flag occurs outside any sitevisit window (Ind_1 = 0), and 0 otherwise. In short, 'Ind_4' detects freezing conditions, while 'Ind_4.1' isolates freezing conditions that are not artifacts of site visits.
    """
    """ Shouldn't we probably just keep the same column that has the better flag? Why do we keep Ind_4? """
    def check_ice(self):
        if self.verbose: print("Checking Issues with Ice (Ind_4 and 4.1)")
        self.dataframe['Ind_4'] = ''
        self.dataframe['Ind_4'] = np.where(self.dataframe["WaterTemp_EXO"] <= 0, 1, 0)

        self.dataframe['Ind_4.1'] = None
        self.dataframe['Ind_4.1'] = np.where((self.dataframe['Ind_4'] == 1) & (self.dataframe['_FieldNoteFlag'] == 0), 1, 0)
    
    """
    This method is called for use on Ind_5

    Ehsan's Comments on this function:
        Map each event number k to (start_idx, end_idx, event_idx):
        start_idx: row holding 'Starting time of Event k' (the Standard row just before the event)
        end_idx:   row holding 'Ending time of Event k' (the Standard row just after the event)
        event_idx: rows that belong to event k (Event_Counter == k)
        Events are matched by number (not by scanning for the next start/end marker), because the
        markers of adjacent events interleave, and because the marker rows themselves are normal rows
        that must not be filtered out.
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
    Section 3.2.4 - Step 4
    Fourth, the code checks for issues related to sensor exposure to air. This code uses an 'LWL' flag to identify when the sensor is exposed to air. Four different conditions are checked to verify that a sensor is out of the water and exposed to air or not. 
     - Checking conditions such as sharp changes in values of specific conductance, comparing air temperature with water temperature, and examining the stage of water can help identify when the sensor is not submerged in the water. A new column called 'Ind_5.1' is created to check the drop changes at the beginning and end of each anomaly event, indicating that the surrounding sensor condition changed. 'Ind_5.1' checks each non-calibration event window and fills all rows for events with a value of 1 if both the start- and end-boundary jumps in the raw data series exceed a threshold, 'ThrV_1'. Otherwise 'Ind_5.1' is set to 0 (Figure 4). 'ThrV_1' is a predefined threshold that is defined in the settings for the object.
    """
    def delta_start_end(self):
        if self.verbose: print("Delta Start/End...")
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
     - A new column called 'Ind_5.2' is then created to check the specific conductance of water, as conductivity measured by the specific conductance sensor is dramatically reduced when the sensor is exposed to air. The 'Ind_5.2' column is filled with a value of 1 on timesteps outside calibration windows when specific conductance is missing or below a set threshold, 'ThrV_2'. 'ThrV_2' is a predefined threshold that is defined in the 'Initial_Settings.yaml' file. 
    """
    def check_spCond(self):
        if self.verbose: print("Checking Specific Conductance...")
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
      - Then, a new column called 'Ind_5.3' is created to compare the average water temperature and air temperature for each anomaly event period. The 'Ind_5.3' column is filled with 1 when the average absolute difference between water and air temperature (|Water Temperature - Air Temperature|) over the event is small (below 'ThrV_3' set in the 'Initial_Settings.yaml' file), suggesting the aquatic sensor is exposed to air. 
    """
    def compare_temps(self):
        if self.verbose: print("Checking Water and Air Temperatures...")
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
      - A column called 'Ind_5.4' is then created in the data frame to compare the average water stage within a buffer of time before and after the anomaly event, and to compare the difference with the average water stage during the anomaly event. The code calculates the n-point averages before and after the event (Figure 5). If both are greater than a threshold 'ThrV_4', it indicates that the water level is reduced and the sensor may be exposed to air. In this case, the 'Ind_5.4' column is filled with 1; otherwise, 0. The 'n' and 'ThrV_4' are predefined thresholds that are defined in the 'Initial_Settings.yaml' file. 
    """
    def compare_ave_stage(self):
        if self.verbose: print("Checking Average Stage...")
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
      - Finally, a new column called 'Ind_5' is created to composite the prior logic. The 'Ind_5' column is set to 1 only if 'Ind_5.4' = 1 and at least one of 'Ind_5.1'/ 'Ind_5.2' / 'Ind_5.3' = 1 (else 0, or None if prerequisites are missing), yielding a robust out of water indicator.
    """
    """ Again, shouldn't we delete some of the indicies that we don't need? """


