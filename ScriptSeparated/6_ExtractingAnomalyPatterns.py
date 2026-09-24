#%% 
# 6. Extracting anomaly patterns  ##############################################################################################################################################################

## 6.1. `Ind_1` Where Field Notes Exist ===================================================================================================

def update_ind2_based_on_events(df, Variable, CalibrationList):
    df.index = pd.to_datetime(df.index)                                             # Ensure the index is in datetime format
    df['Ind_1'] = 0                                                                 # Initialize 'Ind_1' to 0 for all rows

    # Create a dictionary to store event start ('B') and end ('N') times
    event_dict = {}
    for event in df['Event Number'].dropna().unique():
        event_rows = df[df['Event Number'] == event]
        if event.startswith('B'):
            event_dict[event] = event_rows.index[0]
        elif event.startswith('N'):
            event_dict[event] = event_rows.index[0]

    # Flag to ensure the calibration message is displayed only once
    calibration_ignored_message_displayed = False

    # Iterate through the event dictionary to update 'Ind_1'
    for i in range(1, int(len(event_dict) / 2) + 1):
        begin_time = event_dict.get(f'B{i}', None)
        end_time = event_dict.get(f'N{i}', None)
        if begin_time and end_time:
            print(f"Updating 'Ind_1' for range: {begin_time} to {end_time}")
            # Identify rows within the range using the index
            mask = (df.index >= begin_time) & (df.index <= end_time)

            # Build a regex pattern to match any of the keywords in the list
            calibration_exists = r'\b(' + '|'.join(re.escape(keyword) for keyword in CalibrationList) + r')\b'

            if Variable == 'WaterTemp_EXO':
                if not calibration_ignored_message_displayed:
                    print("\033[94mNote: Calibration is ignored when 'Variable' is 'WaterTemp_EXO'\033[0m")
                    calibration_ignored_message_displayed = True
                df.loc[mask, 'Ind_1'] = 1
            else:
                # Apply calibration logic for other variables
                df['Contains_Cal'] = df['Method'].str.contains(calibration_exists, case=False, na=False)
                df['Extracted_Cal_Words'] = df['Method'].str.findall(calibration_exists, flags=re.IGNORECASE)

                if df['Contains_Cal'].any():
                    df.loc[mask, 'Ind_1'] = 2
                else:
                    df.loc[mask, 'Ind_1'] = 1

    return df


# Apply the function to update 'Ind_1'
df_all_Ind1 = update_ind2_based_on_events(df_all, Variable, CalibrationList)

"""
# Saving:
os.chdir(Results_folder)
output_path_with_index = "File_10. Df_all_Ind1.xlsx"
df_all_Ind1.to_excel(output_path_with_index, index=True)
print("Ind_1 successfully updated based on event ranges and calibration logic and saved to: File_10. Df_all_Ind1.xlsx")
"""
#%%

## 6.2. Anomaly Event Identification ======================================================================================================

### 6.2.1. Calibration Event Identification ---------------------------------------------------------------------------------------

if Variable == 'WaterTemp_EXO':
    print("\033[94mSkipping Calibration Events Identification as 'Variable' is 'WaterTemp_EXO'\033[0m")
else:
    print("Proceeding with Calibration Events Identification")

    def process_calibration_events(df):
        # Initialize the calibration counter and lists for annotations
        cal_counter = 0
        cal_counter_list = []
        cal_start_annotations = [None] * len(df)
        cal_end_annotations = [None] * len(df)
        
        # Flag to track if inside a calibration event
        inside_event = False

        # Iterate through each row in the DataFrame
        for i in range(len(df)):
            if df.iloc[i]['Ind_1'] == 2:  # If it's a calibration event
                if not inside_event:
                    # Entering a new calibration event
                    cal_counter += 1
                    inside_event = True
                    cal_start_annotations[i] = f'Starting time of CalB{cal_counter}'
                
                # Add the current calibration number to the counter list
                cal_counter_list.append(cal_counter)
                
                # Check if it's the end of the calibration event (next row is not a calibration event)
                if i + 1 < len(df) and df.iloc[i + 1]['Ind_1'] != 2:
                    cal_end_annotations[i] = f'Ending time of CalN{cal_counter}'
                    inside_event = False  # Exit the calibration event
            else:
                # Outside of a calibration event
                cal_counter_list.append(0)
                inside_event = False

        # Add the annotations to the DataFrame
        df['Cal_Counter'] = cal_counter_list
        df['CalStartTime'] = cal_start_annotations
        df['CalEndTime'] = cal_end_annotations

        return df

    # Apply the function to identify calibration events
    df_all_Ind1 = process_calibration_events(df_all_Ind1)

"""
# Saving:
os.chdir(Results_folder)
output_path_with_index = "File_11. Df_all_CAL.xlsx"
df_all_Ind1.to_excel(output_path_with_index, index=True)
output_path_with_index
print("Calibration events successfully identified and saved to: File_11. Df_all_CAL.xlsx")
"""

#%% 
### 6.2.2. "AffectedbyCal" Events Identification ----------------------------------------------------------------------------------

# Step 1: Calculating QC-Raw ("QCRawColumn") -----------------------------------------------
# RawQCColumn: Calculating differences point-by-point
df_all_Ind1['RawQCColumn'] = df_all_Ind1[f'{Variable}_QC1'] - df_all_Ind1[f'{Variable}_QC0']
df_all_Ind1_RawQCColumn = df_all_Ind1

# Checking for running/skipping the calibration identification step based on the variable whether the 'Variable' is 'WaterTemp_EXO' or not.
if Variable == 'WaterTemp_EXO':
    print("\033[94mSkipping AffectedbyCal Events Identification as Variable is 'WaterTemp_EXO'\033[0m")
else:
    print("Proceeding with AffectedbyCal Events Identification")

    # Step 2: Calculating "iMinePrei" = "i-(i-1)" for "RawQCColumn" column -----------------
    # Calculate the difference between each row and its previous row
    df_all_Ind1['iMinePrei'] = df_all_Ind1['RawQCColumn'].diff()

    # Step 3: Classifying the "AffectedbyCal" types and filling in "CorrectionTypeCal" -----
    def classify_calibration(df):
        def is_valid_numeric(x):
            """ Check if x is a valid numeric value (not 0, not NaN, and not -9999). """
            try:
                if pd.isna(x):
                    return False
                x_float = float(x)
                if x_float == 0 or x_float == -9999:
                    return False
                return True
            except Exception:
                return False

        def classify_calibration_row(row):
            """ Classifies each row into 'CS' or 'LDC'. """
            if row['Ind_1'] == 0:
                if row['iMinePrei'] == 0 and is_valid_numeric(row['RawQCColumn']):
                    return 'CS'
                elif is_valid_numeric(row['iMinePrei']) and is_valid_numeric(row['RawQCColumn']):
                    return 'LDC'
            return None

        df = df.reset_index(drop=False)
        df['CorrectionTypeCal'] = df.apply(classify_calibration_row, axis=1)

        # Propagate classification to the previous row
        for i in range(1, len(df)):
            if df.at[i, 'CorrectionTypeCal'] in ['CS', 'LDC']:
                df.at[i - 1, 'CorrectionTypeCal'] = df.at[i, 'CorrectionTypeCal']

        return df

    # Apply function
    df_all_Ind1 = classify_calibration(df_all_Ind1)

    #  Step 4: 'CalibrationType' counter -----------------------------------------------------
    def assign_affected_by_cal_counter(df):
        df = df.reset_index(drop=True)
        df['AffectedbyCal_Counter'] = 0
        counter = 0
        propagate = False

        for i in range(len(df)):
            if pd.notna(df.iloc[i]['CorrectionTypeCal']):
                if not propagate:
                    counter += 1
                df.at[i, 'AffectedbyCal_Counter'] = counter
                propagate = True
            else:
                propagate = False

        return df
    df_all_Ind1 = assign_affected_by_cal_counter(df_all_Ind1)

    #  Step 5: Starting point of each affected event by calibration --------------------------
    def add_affected_cal_times(df):
        df['AffectedCalStartTime'] = None
        df['AffectedCalEndTime'] = None

        affected_groups = df['AffectedbyCal_Counter'].unique()
        affected_groups = [g for g in affected_groups if g != 0]

        for group in affected_groups:
            group_rows = df[df['AffectedbyCal_Counter'] == group]
            if not group_rows.empty:
                start_index = group_rows.index[0]
                end_index = group_rows.index[-1]
                df.at[start_index, 'AffectedCalStartTime'] = f'Starting time of Affected Cal {group}'
                df.at[end_index, 'AffectedCalEndTime'] = f'Ending time of Affected Cal {group}'

        return df
    df_all_Ind1 = add_affected_cal_times(df_all_Ind1)

    """
    #  Saving `Df_all_AffectedByCAL`
    os.chdir(Results_folder)
    output_path_with_index = "File_12. Df_all_AffectedByCAL.xlsx"
    df_all_Ind1.to_excel(output_path_with_index, index=True)
    print("AffectedbyCal events ranges successfully identified and saved to: File_12. Df_all_AffectedByCAL.xlsx")
    """
    
    #  Step 6: Generating the `AffectedbyCal` events' list ---------------------------------
    def create_affected_events_df(df):
        affected_df = df[df['AffectedbyCal_Counter'] > 0]
        
        affected_events = affected_df.groupby('AffectedbyCal_Counter').agg({
            'AffectedCalStartTime': 'first',
            'AffectedCalEndTime': 'first',
            'CorrectionTypeCal': lambda x: ', '.join(map(str, x.unique()))}).reset_index()

        affected_events['Start time'] = affected_events['AffectedCalStartTime'].map(
            lambda x: df.loc[df['AffectedCalStartTime'] == x, 'LocalDateTime'].values[0] 
            if pd.notna(x) else None)

        affected_events['End time'] = affected_events['AffectedCalEndTime'].map(
            lambda x: df.loc[df['AffectedCalEndTime'] == x, 'LocalDateTime'].values[0] 
            if pd.notna(x) else None)

        affected_events.rename(columns={'CorrectionTypeCal': 'Correction Type'}, inplace=True)
        affected_events = affected_events[['Start time', 'End time', 'Correction Type', 'AffectedbyCal_Counter']]

        return affected_events

    df_affected_events = create_affected_events_df(df_all_Ind1)

"""
#  Saving `AffectedbyCal events list`
os.chdir(Results_folder)
output_path_with_index = "File_13. AffectedbyCal events list.xlsx"
df_affected_events.to_excel(output_path_with_index, index=True)
print("AffectedbyCal events list successfully saved to: File_13. AffectedbyCal events list.xlsx")
"""  

#%% 
### 6.2.3. Checking for Overlap Other Anomalies with `AffectedbyCal` Event --------------------------------------------------------

if Variable == 'WaterTemp_EXO':
    print("\033[94mSkipping checking for Overlap Other Anomalies with `AffectedbyCal`, as 'Variable' is 'WaterTemp_EXO'\033[0m")
else:
    print("Proceeding with cchecking for Overlap Other Anomalies with `AffectedbyCal` Event")

    # Part 1: Filtering & Linear Regression ----------------------------------------------
    def detect_linear_trend(df):
        df['LinearFit_R2'] = np.nan  # Initialize R² column

        # Filter only calibration events with 'Constant Shift' or 'Linear Drift Correction'
        filtered_df = df[df['CorrectionTypeCal'].isin(['Constant Shift', 'Linear Drift Correction'])]

        for affected_id in filtered_df['AffectedbyCal_Counter'].unique():
            affected_rows = filtered_df[filtered_df['AffectedbyCal_Counter'] == affected_id].copy()
            indices = affected_rows.index

            # Apply Linear Regression only for 'Linear Drift Correction'
            if affected_rows['CorrectionTypeCal'].iloc[0] == 'Linear Drift Correction':
                X = np.arange(len(affected_rows)).reshape(-1, 1)
                y = affected_rows['RawQCColumn'].values
                model = LinearRegression()
                model.fit(X, y)
                y_pred = model.predict(X)
                r2_score = model.score(X, y)
                df.loc[indices, 'LinearFit_R2'] = r2_score  # Store R² value

        return df
    # Apply the function to detect linear trends in "Linear Drift Correction" events
    df_all_Ind1 = detect_linear_trend(df_all_Ind1)

    # Part 2: Detecting Spikes & Residual Deviations -----------------------------------

    def detect_spikes_and_residual_anomalies(df, anomaly_thresh=0.001, z_thresh=3):
        df['OverlapAnomalyDetected'] = 0  # Initialize anomaly flag
        df['SpikeDetected'] = 0  # Initialize spike flag

        filtered_df = df[df['CorrectionTypeCal'].isin(['Constant Shift', 'Linear Drift Correction'])]

        for affected_id in filtered_df['AffectedbyCal_Counter'].unique():
            affected_rows = filtered_df[filtered_df['AffectedbyCal_Counter'] == affected_id].copy()
            indices = affected_rows.index

            y = affected_rows['RawQCColumn'].values

            # Detect deviations from constant shift
            if affected_rows['CorrectionTypeCal'].iloc[0] == 'Constant Shift':
                mean_value = np.mean(y)  # Expected constant value
                residuals = np.abs(y - mean_value)  # Deviation from the constant shift
                anomaly_indices = indices[residuals > anomaly_thresh]
                df.loc[anomaly_indices, 'OverlapAnomalyDetected'] = 1  # Mark anomalies

            # Detect spikes using Z-score
            z_scores = np.abs(zscore(y))
            spike_indices = indices[z_scores > z_thresh]
            df.loc[spike_indices, 'SpikeDetected'] = 1  # Mark spikes

        return df
    # Apply function to detect spikes and residual anomalies
    df_all_Ind1 = detect_spikes_and_residual_anomalies(df_all_Ind1)

    # Part 3: Detecting Nonlinear Drift & Storing Results ------------------------------

    def detect_nonlinear_drift_and_store_results(df):
        df['NonlinearDriftDetected'] = 0  # Initialize drift flag

        filtered_df = df[df['CorrectionTypeCal'].isin(['Constant Shift', 'Linear Drift Correction'])]

        for affected_id in filtered_df['AffectedbyCal_Counter'].unique():
            affected_rows = filtered_df[filtered_df['AffectedbyCal_Counter'] == affected_id].copy()
            indices = affected_rows.index

            # Second-order difference test for nonlinear drift detection
            df.loc[indices, 'SecondDiff'] = df['RawQCColumn'].diff().diff()
            nonlinear_drift_indices = indices[df.loc[indices, 'SecondDiff'].abs() > df.loc[indices, 'SecondDiff'].std()]
            df.loc[nonlinear_drift_indices, 'NonlinearDriftDetected'] = 1  # Mark nonlinear drift

        # Add a column to indicate if anomalies exist in each affected event
        df['Has_OverlapAnomalies'] = df['AffectedbyCal_Counter'].map(
            lambda x: df[df['AffectedbyCal_Counter'] == x][['OverlapAnomalyDetected', 'SpikeDetected', 'NonlinearDriftDetected']].sum().sum() > 0
        )

        # Add extracted anomalies directly to df_all_Ind1
        df['Extracted_Anomalies'] = df.apply(
            lambda row: (row['LocalDateTime'], row['RawQCColumn']) 
            if row['OverlapAnomalyDetected'] == 1 or row['SpikeDetected'] == 1 or row['NonlinearDriftDetected'] == 1 else None, 
            axis=1
        )
        return df

    # Apply function to detect nonlinear drift and store results
    df_all_Ind1 = detect_nonlinear_drift_and_store_results(df_all_Ind1)

"""
# Saving `Df_all_OverlapWithCAL`
os.chdir(Results_folder)
output_path_with_index = "File_14. Df_all_OverlapWithCAL.xlsx"
df_all_Ind1.to_excel(output_path_with_index, index=True)
print("Overlap with other anomalies successfully checked and saved to: File_14. Df_all_OverlapWithCAL.xlsx")
"""

#%% 
### 6.2.4. `Ind_2` -----------------------------------------------------------------------------------------------------------------

# Defining `Ind_2` based on variable type ------------------------------------------------

def assign_Ind2(row, Variable):
    if Variable == 'WaterTemp_EXO':
        # Simplified logic for 'WaterTemp_EXO' that ignores calibration events
        if pd.isna(row.get(f'{Variable}_QC0', np.nan)) or row.get(f'{Variable}_QC0', np.nan) == -9999:
            return 1
        elif pd.isna(row.get(f'{Variable}_QC1', np.nan)) or row.get(f'{Variable}_QC1', np.nan) == -9999:
            return 3
        elif row.get('RawQCColumn', np.nan) == 0:
            return 0
        else:
            return 2  # Default value
    else:
        # Full logic for other variables
        if row['Ind_1'] == 2:
            return 4
        elif row['CorrectionTypeCal'] in ['CS', 'LDC']:
            return 5
        elif pd.isna(row.get(f'{Variable}_QC0', np.nan)) or row.get(f'{Variable}_QC0', np.nan) == -9999:
            return 1
        elif pd.isna(row.get(f'{Variable}_QC1', np.nan)) or row.get(f'{Variable}_QC1', np.nan) == -9999:
            return 3
        elif row.get('RawQCColumn', np.nan) == 0:
            return 0
        else:
            return 2  # Default value

# Apply the function row-wise
df_all_Ind1['Ind_2'] = df_all_Ind1.apply(assign_Ind2, axis=1, args=(Variable,))

# Handling `Non-standard` TimeIntervals
# Apply 'TimeInterval' condition separately without modifying previous logic
df_all_Ind1.loc[df_all_Ind1['TimeInterval'] == 'Non-standard', 'Ind_2'] = np.nan

# Identify event indices where Ind_2 is 1, 2, 3, or 4
event_mask = df_all_Ind1['Ind_2'].isin([1, 2, 3, 4])
event_indices = df_all_Ind1[event_mask].index

# Iterate over event indices to adjust Ind_2 for 'Non-standard' TimeInterval rows before/after events
for idx in event_indices:
    prev_idx = df_all_Ind1.index.get_loc(idx) - 1
    next_idx = df_all_Ind1.index.get_loc(idx) + 1

    # Ensure the previous row exists and has 'Non-standard' TimeInterval
    if prev_idx >= 0 and df_all_Ind1.iloc[prev_idx]['TimeInterval'] == 'Non-standard':
        df_all_Ind1.iloc[prev_idx, df_all_Ind1.columns.get_loc('Ind_2')] = df_all_Ind1.loc[idx, 'Ind_2']

    # Ensure the next row exists and has 'Non-standard' TimeInterval
    if next_idx < len(df_all_Ind1) and df_all_Ind1.iloc[next_idx]['TimeInterval'] == 'Non-standard':
        df_all_Ind1.iloc[next_idx, df_all_Ind1.columns.get_loc('Ind_2')] = df_all_Ind1.loc[idx, 'Ind_2']

# Store results
df_all_Ind1_Ind2 = df_all_Ind1

"""
# saving
os.chdir(Results_folder)
output_path_with_index = "File_15. df_all + Ind1 + Ind2.xlsx"
df_all_Ind1_Ind2.to_excel(output_path_with_index, index=True)
print("Ind_2 successfully assigned based on conditions and saved to: File_15. df_all + Ind1 + Ind2.xlsx")
"""

#%% 
## 6.3. Counter of the Events =============================================================================================================

# Initializing Event Counter -----------------------------------------------------

# Initialize the event counter and list to store event numbers
event_counter = 0
event_counter_list = []
inside_event = False  # Flag to track if we're inside an event
previous_ind2 = None  # Store previous row's Ind_2 value

# Determine which code block to use based on the selected 'Variable'
if Variable == 'WaterTemp_EXO':
    # Simplified event detection logic for 'WaterTemp_EXO'
    for ind in df_all_Ind1_Ind2['Ind_2']:
        if ind in [1, 2, 3]:  # Check if it's an event
            if not inside_event or (previous_ind2 is not None and ind != previous_ind2):
                event_counter += 1
                inside_event = True
            event_counter_list.append(event_counter)
        else:
            event_counter_list.append(0)  # No event, reset to 0
            inside_event = False
        previous_ind2 = ind
else:
    # Full event detection logic for other variables
    for ind in df_all_Ind1_Ind2['Ind_2']:
        if ind in [1, 2, 3, 4, 5]:  # Check if it's an event
            if not inside_event or (previous_ind2 is not None and ind != previous_ind2):
                event_counter += 1
                inside_event = True
            event_counter_list.append(event_counter)
        else:
            event_counter_list.append(0)  # No event, reset to 0
            inside_event = False
        previous_ind2 = ind

# Add this list as a new column 'Event_Counter' in the dataframe
df_all_Ind1_Ind2['Event_Counter'] = event_counter_list

"""
#saving
os.chdir(Results_folder)
output_path_with_index = "File_15.1 df_all + Ind1 + Ind2.xlsx"
df_all_Ind1_Ind2.to_excel(output_path_with_index, index=True)
print("Event Counter successfully assigned and saved to: File_15.1 df_all + Ind1 + Ind2.xlsx")
"""

#%%
#%% 
## 6.4. Start time and End time of each event =============================================================================================

### 6.4.1. Start and End Time of Each Event for AffectedCal events ----------------------------------------------------------------
if Variable == 'WaterTemp_EXO':
    print("\033[94mSkipping Start and End Time Columns for AffectedCal events, as 'Variable' is 'WaterTemp_EXO'\033[0m")
else:
    print("Proceeding with Start and End Time Columns for AffectedCal events")
    # Initializing Start and End Time Columns for AffectedCal events ------------------------------------
    # Initialize new columns for storing start and end times
    df_all_Ind1_Ind2['AffectedCalStartTime2'] = None
    df_all_Ind1_Ind2['AffectedCalEndTime2'] = None

    # Initialize tracking variables
    inside_event = False  # Flag to track ongoing events

    for i in range(len(df_all_Ind1_Ind2)):
        if df_all_Ind1_Ind2.iloc[i]['Ind_2'] == 5:  # Only process Ind_2 == 5 events
            if not inside_event:  # If entering a new event
                inside_event = True
                df_all_Ind1_Ind2.at[i, 'AffectedCalStartTime2'] = f'Starting time of Event {df_all_Ind1_Ind2.iloc[i]["Event_Counter"]}'

            # If this is the last row of the event
            if i == len(df_all_Ind1_Ind2) - 1 or df_all_Ind1_Ind2.iloc[i + 1]['Ind_2'] != 5:
                df_all_Ind1_Ind2.at[i, 'AffectedCalEndTime2'] = f'Ending time of Event {df_all_Ind1_Ind2.iloc[i]["Event_Counter"]}'
                inside_event = False  # Exit the event

"""
#saving
os.chdir(Results_folder)
output_path_with_index = "File_15.2.xlsx"
df_all_Ind1_Ind2.to_excel(output_path_with_index, index=True)
print("Event Counter successfully assigned and saved to: File_15.2.xlsx")
"""

#%%
### 6.4.2. Start and End Time of Each Event for Other Events ----------------------------------------------------------------------

# Initialize columns based on Variable
if Variable == 'WaterTemp_EXO':
    print("\033[94mProceeding with WaterTemp_EXO-specific event processing\033[0m")
    
    # Reset the index to avoid index misalignment issues and ensure sequential indexing
    df_all_Ind1_Ind2.reset_index(drop=True, inplace=True)

    # Recalculate the total number of rows after resetting the index
    num_rows = len(df_all_Ind1_Ind2)

    # Reinitialize 'StartTimeEvent' and 'EndTimeEvent' columns
    df_all_Ind1_Ind2['StartTimeEvent'] = None
    df_all_Ind1_Ind2['EndTimeEvent'] = None

    # Process each row to identify anomaly events
    for i in range(num_rows):
        event_counter = df_all_Ind1_Ind2.loc[i, 'Event_Counter']
        
        # Only process rows where Event_Counter > 0
        if event_counter > 0:
            # Check if this is the start of an event
            if i == 0 or df_all_Ind1_Ind2.loc[i - 1, 'Event_Counter'] != event_counter:
                start_idx = i - 1
                # Search backwards for the exact previous 'Standard' row if possible
                while start_idx >= 0 and df_all_Ind1_Ind2.loc[start_idx, 'TimeInterval'] != 'Standard':
                    start_idx -= 1
                if start_idx < 0:
                    start_idx = 0  # Edge case: event at the very beginning
                df_all_Ind1_Ind2.loc[start_idx, 'StartTimeEvent'] = f'Starting time of Event {event_counter}'
            
            # Check if this is the end of an event
            if i == num_rows - 1 or df_all_Ind1_Ind2.loc[i + 1, 'Event_Counter'] != event_counter:
                end_idx = i + 1
                # Search forward for the first 'Standard' row after the event if possible
                while end_idx < num_rows and df_all_Ind1_Ind2.loc[end_idx, 'TimeInterval'] != 'Standard':
                    end_idx += 1
                # If we reach the end of the DataFrame, set the last row as the end of the event
                if end_idx >= num_rows:
                    end_idx = num_rows - 1
                
                # Correctly set the EndTimeEvent with the proper LocalDateTime
                df_all_Ind1_Ind2.loc[end_idx, 'EndTimeEvent'] = f'Ending time of Event {event_counter}'

else:
    # Identifying Start and End of Other Event Types -----------------------------
    print("\033[94mSkipping WaterTemp_EXO-specific processing, running the general event processing instead\033[0m")
    # Initialize columns to store start and end time annotations
    df_all_Ind1_Ind2['OtherStartTime'] = None
    df_all_Ind1_Ind2['OtherEndTime'] = None

    # Get the total number of rows
    num_rows = len(df_all_Ind1_Ind2)

    # Step 1: Iterate through the DataFrame to find event boundaries
    for i in range(num_rows):
        event_counter = df_all_Ind1_Ind2.iloc[i]['Event_Counter']
        ind_2_value = df_all_Ind1_Ind2.iloc[i]['Ind_2']
        
        # Apply only to events where Ind_2 is NOT 5
        if event_counter > 0 and ind_2_value != 5:
            
            ### Step 2: Find the previous `Standard` row for the start time ###
            if i == 0 or df_all_Ind1_Ind2.iloc[i - 1]['Event_Counter'] != event_counter:
                start_idx = i - 1  # Look at the previous row
                
                # Search backward for a `Standard` row
                while start_idx >= 0 and df_all_Ind1_Ind2.iloc[start_idx]['TimeInterval'] != 'Standard':
                    start_idx -= 1  
                
                # Exception: If at the first row, assign the first row
                if start_idx < 0:
                    start_idx = 0  

                df_all_Ind1_Ind2.at[start_idx, 'OtherStartTime'] = f'Starting time of Event {event_counter}'

            ### Step 3: Find the next `Standard` row for the end time ###
            if i == num_rows - 1 or df_all_Ind1_Ind2.iloc[i + 1]['Event_Counter'] != event_counter:
                end_idx = i + 1  # Look at the next row
                
                # Search forward for a `Standard` row
                while end_idx < num_rows and df_all_Ind1_Ind2.iloc[end_idx]['TimeInterval'] != 'Standard':
                    end_idx += 1  
                
                # Exception: If at the last row, assign the last row
                if end_idx >= num_rows:
                    end_idx = num_rows - 1  

                df_all_Ind1_Ind2.at[end_idx, 'OtherEndTime'] = f'Ending time of Event {event_counter}'

    # Merging Start and Ending Time Columns ---------------------------------------
    df_all_Ind1_Ind2['StartTimeEvent'] = df_all_Ind1_Ind2['AffectedCalStartTime2'].combine_first(df_all_Ind1_Ind2['OtherStartTime'])
    df_all_Ind1_Ind2['EndTimeEvent'] = df_all_Ind1_Ind2['AffectedCalEndTime2'].combine_first(df_all_Ind1_Ind2['OtherEndTime'])

#%%
## 6.5. Identify events where the raw data is repeated ================================================================================================

# Initialize the 'RepeatedEvent' column
df_all_Ind1_Ind2['RepeatedEvent'] = np.nan

# optional but recommended: stabilize float equality (keep if your data are floats)
key = df_all_Ind1_Ind2[f'{Variable}_QC0'].round(4)

mask_pos = df_all_Ind1_Ind2['Event_Counter'] > 0
repeats = (
    df_all_Ind1_Ind2.loc[mask_pos]
      .groupby('Event_Counter')[key.name]
      .transform(lambda s: s.duplicated(keep=False) & s.notna())
)

df_all_Ind1_Ind2.loc[mask_pos, 'RepeatedEvent'] = repeats.fillna(False).astype(int)

#%%
## 6.6 Identify Spike within Event ================================================================================================================

# Initialize the 'Spike' column
df_all_Ind1_Ind2['Spike'] = np.nan

# --- 1) Helper: robust z-score using local neighborhood (MAD) ---
def robust_spike_flag(series, center_idx, window=3, thresh=6.0, min_neighbors=2):
    """
    series: the full column (pd.Series) to compute neighbors from (aligned with df index)
    center_idx: the index label (not position) of the candidate row
    window: number of rows to look backward/forward (by position)
    thresh: threshold for robust z-score (|x - median| / (1.4826*MAD))
    min_neighbors: require at least this many neighbors to attempt detection
    """
    # position of center
    try:
        pos = series.index.get_loc(center_idx)
    except KeyError:
        return np.nan  # index not found

    # slice neighborhood by position
    start = max(0, pos - window)
    end   = min(len(series), pos + window + 1)

    neighborhood = series.iloc[start:end].drop(index=center_idx, errors='ignore')

    # need enough neighbors
    neighborhood = neighborhood.dropna()
    if len(neighborhood) < min_neighbors:
        return 0  # not enough context → call it not spike (or return np.nan if you prefer)

    x = series.loc[center_idx]

    med = np.median(neighborhood.values)
    mad = np.median(np.abs(neighborhood.values - med))

    if mad == 0:
        # fallback to std-based z-score
        std = neighborhood.std(ddof=0)
        if std == 0 or np.isnan(std):
            # final fallback: absolute diff vs median with a tight epsilon
            return int(np.abs(x - med) > 1e-6)
        z = np.abs((x - med) / std)
        return int(z > 6.0)  # stricter when using std
    else:
        # 1.4826 makes MAD comparable to std under normality
        rzs = np.abs((x - med) / (1.4826 * mad))
        return int(rzs > thresh)

# --- 2) Build masks: singleton events + valid numeric QC0 ---
# event size per row
event_size = df_all_Ind1_Ind2.groupby('Event_Counter')['Event_Counter'].transform('size')

# singleton event rows (and positive event id; drop this if 0/neg are valid)
singleton_mask = (event_size == 1) & (df_all_Ind1_Ind2['Event_Counter'] > 0)

# valid QC0 (numeric, not NaN, not -9999)
valid_qc0_mask = df_all_Ind1_Ind2[f'{Variable}_QC0'].notna() & (df_all_Ind1_Ind2[f'{Variable}_QC0'] != -9999)

candidates_mask = singleton_mask & valid_qc0_mask

# --- 3) Fill Spike for candidates using robust neighborhood test ---
"""
NOTE: the neighborhood uses positional neighbors in the *full* dataframe, not restricted to the same event (since the event has only one row).
    If you want to restrict neighbors to normal (non-event) rows, you can mask them before calling the function.
"""
# Default everything remains NaN (as you set). We'll write 0/1 only for candidates.
for idx in df_all_Ind1_Ind2.index[candidates_mask]:
    flag = robust_spike_flag(
        series=df_all_Ind1_Ind2[f'{Variable}_QC0'],
        center_idx=idx,
        window=3,          # look 3 rows before and after
        thresh=6.0,        # robust z-score threshold
        min_neighbors=2    # need at least 2 neighbors
    )
    df_all_Ind1_Ind2.at[idx, 'Spike'] = flag

#%%
## 6.7 Assigning the anomalies patterns ===============================================================================================

def assign_anomaly_pattern(df: pd.DataFrame, Variable: str) -> pd.DataFrame:
    """
    Fill df['AnomalyPattern'] using:
      - WaterTemp_EXO: Ind_2(1→1, 3→2), RepeatedEvent(1→3), Spike(1→4), else 7
      - Other vars:    LinearDrift→5, CS→6, then Ind_2(1→1, 3→2),
                       RepeatedEvent(1→3), Spike(1→4), else 7
    Priority is left→right in each list.
    """

    df_all_Ind1_Ind2['AnomalyPattern'] = np.nan

    if Variable == 'WaterTemp_EXO':
        conds = [
            df_all_Ind1_Ind2['Ind_2'].eq(1),
            df_all_Ind1_Ind2['Ind_2'].eq(3),
            df_all_Ind1_Ind2['RepeatedEvent'].eq(1),
            df_all_Ind1_Ind2['Spike'].eq(1),
        ]
        choices = [1, 2, 3, 4]
        df_all_Ind1_Ind2['AnomalyPattern'] = np.select(conds, choices, default=7)

    else:
        # Calibration-related classes come FIRST (highest priority)
        conds = [
            df_all_Ind1_Ind2['CorrectionTypeCal'].eq('LDC'),  # → 5
            df_all_Ind1_Ind2['CorrectionTypeCal'].eq('CS'),          # → 6
            df_all_Ind1_Ind2['Ind_2'].eq(1),                                    # → 1
            df_all_Ind1_Ind2['Ind_2'].eq(3),                                    # → 2
            df_all_Ind1_Ind2['RepeatedEvent'].eq(1),                            # → 3
            df_all_Ind1_Ind2['Spike'].eq(1),                                    # → 4
        ]
        choices = [5, 6, 1, 2, 3, 4]
        df_all_Ind1_Ind2['AnomalyPattern'] = np.select(conds, choices, default=7)


    # integer output
    df_all_Ind1_Ind2['AnomalyPattern'] = df_all_Ind1_Ind2['AnomalyPattern'].astype('int64')
    return df_all_Ind1_Ind2

# call the function to assign anomaly patterns
df_all_Ind1_Ind2 = assign_anomaly_pattern(df_all_Ind1_Ind2, Variable)

"""
# Saving DataFrame
os.chdir(Results_folder)
output_path_with_index = "File_15.3 df_all + Ind1 + Ind2 + Time.xlsx"
df_all_Ind1_Ind2.to_excel(output_path_with_index, index=True)
print("Start/End time and type of each event successfully identified and saved to: File_15.3 df_all + Ind1 + Ind2 + Time.xlsx")
"""


