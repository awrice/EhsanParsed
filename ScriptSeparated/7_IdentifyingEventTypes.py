
#%% 
## 7. Identifying Event Types, Categories, and assigning the labels ==============================================================================================

# 7.1. Identify Event Types: CAL, CorrectionTypeCal, and OtherType ---------------------------------------------------------------------------------------------

if Variable == 'WaterTemp_EXO':
    print("\033[94mSkipping Identifying Event Types / Categories, as 'Variable' is 'WaterTemp_EXO'\033[0m")
else:
    print("Proceeding with Identifying Event Types / Categories")

    # Step 1: Create a new column 'EventType' initialized as an empty string  --------------------------------
    df_all_Ind1_Ind2['EventType'] = ''

    # Step 2: Assign 'EventType' where 'Ind_2' == 5 (Keep CorrectionTypeCal values) --------------------------
    df_all_Ind1_Ind2.loc[df_all_Ind1_Ind2['Ind_2'] == 5, 'EventType'] = df_all_Ind1_Ind2.loc[df_all_Ind1_Ind2['Ind_2'] == 5, 'CorrectionTypeCal']

    # Ensure 'StartTimeEvent' and 'EndTimeEvent' are properly formatted
    df_all_Ind1_Ind2['StartTimeEvent'] = df_all_Ind1_Ind2['StartTimeEvent'].astype(str).str.strip()
    df_all_Ind1_Ind2['EndTimeEvent'] = df_all_Ind1_Ind2['EndTimeEvent'].astype(str).str.strip()

    # Step 3: Identify event ranges and assign 'CAL' for `Ind_2 = 4`------------------------------------------
    event_start_idx = None
    event_end_idx = None

    for i, row in df_all_Ind1_Ind2.iterrows():
        # Identify the start of an event
        if isinstance(row['StartTimeEvent'], str) and 'Starting time of Event' in row['StartTimeEvent']:
            event_start_idx = i  # Store the start index

        # Identify the end of the event
        if isinstance(row['EndTimeEvent'], str) and 'Ending time of Event' in row['EndTimeEvent']:
            event_end_idx = i  # Store the end index

        # If an event start is detected but no explicit end, use the last row in the event
        if event_start_idx is not None:
            if event_end_idx is None:
                event_end_idx = i  # Use the last detected row if no explicit end is found

            # Apply event type assignment for the detected range
            for j in range(event_start_idx, event_end_idx + 1):
                ind_2_value = df_all_Ind1_Ind2.at[j, 'Ind_2']
                if ind_2_value == 4:
                    df_all_Ind1_Ind2.at[j, 'EventType'] = 'CAL'

            # Reset tracking for the next event *only if* an event fully processed
            if event_end_idx is not None:
                event_start_idx = None
                event_end_idx = None

    # Step 4: Ensure 'CAL' is assigned before 'OtherType' --------------------------------------------------
    df_all_Ind1_Ind2.loc[df_all_Ind1_Ind2['Ind_2'] == 4, 'EventType'] = 'CAL'

    # Step 5: Ensure ALL `Ind_2 = 3, 2, 1` values are assigned `OtherType`, even if they were missed -------
    df_all_Ind1_Ind2.loc[(df_all_Ind1_Ind2['Ind_2'].isin([1, 2, 3])) & (df_all_Ind1_Ind2['EventType'] == ''), 'EventType'] = 'OtherType'

    # Step 6: Ensure 'CorrectionTypeCal' values remain unchanged where Ind_2 = 5 ---------------------------
    df_all_Ind1_Ind2.loc[df_all_Ind1_Ind2['Ind_2'] == 5, 'EventType'] = df_all_Ind1_Ind2['CorrectionTypeCal']

"""
# Saving DataFrame
os.chdir(Results_folder)
output_path_with_index = "File_16. df_all + Ind1 + Ind2 + Counter.xlsx"
df_all_Ind1_Ind2.to_excel(output_path_with_index, index=True)
print("Start/End time and type of each event successfully identified and saved to: File_16. df_all + Ind1 + Ind2 + Counter.xlsx")
"""

#%% 
## 7.2. Cross-Validating "Variable" with "CrossVariable" (Ind_3) =====================================================================================

# Dynamically construct the column name
Checking_var = f"{CrossVariable}_QC0"

# Use the dynamically constructed column in the DataFrame
df_all_Ind1_Ind2['Ind_3'] = np.where(df_all_Ind1_Ind2[Checking_var].isna(), 1, 0)

"""
# Saving the DataFrame
os.chdir(Results_folder)
output_path_with_index = "File_17. df_all + Ind1 + Ind2 + Counter + Ind3.xlsx"
df_all_Ind1_Ind2.to_excel(output_path_with_index, index=True)
print("Ind_3 successfully assigned based on conditions and saved to: File_17. df_all + Ind1 + Ind2 + Counter + Ind3.xlsx")
"""

#%% 
## 7.3 Logic for Anomalies ================================================================================================================

### 7.3.1. 'Ind_4' and 'Ind_4.1' (Checking/ Labelling for ICE events) -------------------------------------------------------------

#### 'Ind_4'Calculation:
df_all_Ind1_Ind2['Ind_4'] = ''
df_all_Ind1_Ind2['Ind_4'] = np.where(df_all_Ind1_Ind2["WaterTemp_EXO_QC0"] <= 0, 1, 0)

#### 'Ind_4.1' Calculation:
df_all_Ind1_Ind2['Ind_4.1'] = None
df_all_Ind1_Ind2['Ind_4.1'] = np.where((df_all_Ind1_Ind2['Ind_4'] == 1) & (df_all_Ind1_Ind2['Ind_1'] == 0), 1, 0)

#%% 
### 7.3.2. Calculating 'Ind_5.1', 'Ind_5.2', 'Ind_5.3', 'Ind_5.4', and 'Ind_5' (Checking/ Labelling for LWL events)----------------

#### 7.3.2.1. 'Ind_5.1' (Condition_I) ----------------------------------------

# Part A: Calculating `delta_Start` and `delta_End`:

def delta_start_end(df, Variable):
    # Reset index and standardize column names
    df.reset_index(inplace=True)
    df.columns = df.columns.str.strip()
    df['LocalDateTime'] = pd.to_datetime(df['LocalDateTime'], errors='coerce')
    df['delta_Start'] = None
    df['delta_End'] = None
    missing_data_flag = "NoData"
    # Filter out rows where `Ind_2` is 4 or 5
    df_filtered = df[~df['Ind_2'].isin([4, 5])].copy().reset_index(drop=True)

    if Variable == 'WaterTemp_EXO':
        # Simplified logic for 'WaterTemp_EXO'
        start_column = 'StartTimeEvent'
        end_column = 'EndTimeEvent'
    else:
        # Full logic for other variables
        start_column = 'OtherStartTime'
        end_column = 'OtherEndTime'

    # Compute `delta_Start`
    for i, row in df_filtered.iterrows():
        if isinstance(row[start_column], str) and 'Starting time of Event' in row[start_column]:
            start_temp = row[f"{Variable}_QC0"]
            if pd.notnull(start_temp):
                for j in range(i + 1, len(df_filtered)):
                    if df_filtered.loc[j, 'TimeInterval'] == 'Standard':
                        next_temp = df_filtered.loc[j, f"{Variable}_QC0"]
                        df_filtered.at[i, 'delta_Start'] = abs(start_temp - next_temp) if pd.notnull(next_temp) else missing_data_flag
                        break
            else:
                df_filtered.at[i, 'delta_Start'] = missing_data_flag

    # Compute `delta_End`
    for i, row in df_filtered.iterrows():
        if isinstance(row[end_column], str) and 'Ending time of Event' in row[end_column]:
            end_temp = row[f"{Variable}_QC0"]
            if pd.notnull(end_temp):
                for j in range(i - 1, -1, -1):
                    if df_filtered.loc[j, 'TimeInterval'] == 'Standard':
                        prev_temp = df_filtered.loc[j, f"{Variable}_QC0"]
                        df_filtered.at[i, 'delta_End'] = abs(end_temp - prev_temp) if pd.notnull(prev_temp) else missing_data_flag
                        break
            else:
                df_filtered.at[i, 'delta_End'] = missing_data_flag

    # Merge computed `delta_Start` and `delta_End` back to the original dataframe
    df.update(df_filtered[['delta_Start', 'delta_End']])
    return df

# Apply the function directly to the DataFrame
df_all_Ind1_Ind2 = delta_start_end(df_all_Ind1_Ind2, Variable)


# Part B: Calculating `Ind_5.1`:
df_all_Ind1_Ind2['Ind_5.1'] = None

if Variable == 'WaterTemp_EXO':
    # Simplified logic for 'WaterTemp_EXO'
    start_column = 'StartTimeEvent'
    end_column = 'EndTimeEvent'
else:
    # Full logic for other variables
    start_column = 'OtherStartTime'
    end_column = 'OtherEndTime'

# Filter out rows where `Ind_2` is 4 or 5
df_filtered = df_all_Ind1_Ind2[~df_all_Ind1_Ind2['Ind_2'].isin([4, 5])].copy().reset_index(drop=True)

# Assign `Ind_5.1` based on delta calculations
for i, row in df_filtered.iterrows():
    if isinstance(row[start_column], str) and 'Starting time of Event' in row[start_column]:
        event_start_idx = i

    if isinstance(row[end_column], str) and 'Ending time of Event' in row[end_column]:
        event_end_idx = i
        if event_start_idx is not None and event_end_idx is not None:
            for j in range(event_start_idx, event_end_idx + 1):
                if df_filtered.at[j, 'Ind_2'] in [4, 5]:
                    continue

                delta_start = df_filtered.at[event_start_idx, 'delta_Start']
                delta_end = df_filtered.at[event_end_idx, 'delta_End']

                if (delta_start not in [None, "NoData"] and delta_end not in [None, "NoData"]):
                    try:
                        delta_start = float(delta_start)
                        delta_end = float(delta_end)
                        df_filtered.at[j, 'Ind_5.1'] = 0
                        if delta_start > ThrV_1 and delta_end > ThrV_1:
                            df_filtered.at[j, 'Ind_5.1'] = 1
                    except ValueError:
                        pass

# Merge computed `Ind_5.1` back to the original dataframe
df_all_Ind1_Ind2.update(df_filtered[['Ind_5.1']])

"""
# Saving the DataFrame
os.chdir(Results_folder)
output_path_with_index = "File_18. Ind5.1.xlsx"
df_all_Ind1_Ind2.to_excel(output_path_with_index, index=True)
print("Ind_5.1 successfully assigned based on conditions and saved to: File_18. Ind5.1.xlsx")
"""

#%%
#### 7.3.2.2. 'Ind_5.2' (Condition_II) -------------------------------------------

# Applying Ind_5.2 Logic:
# Initialize 'Ind_5.2' with None
df_all_Ind1_Ind2['Ind_5.2'] = None

# Apply the condition only for rows where 'Ind_2' is NOT 4 or 5 and 'TimeInterval' is 'Standard'
df_all_Ind1_Ind2['Ind_5.2'] = np.where(
    (~df_all_Ind1_Ind2['Ind_2'].isin([4, 5])) &  # Exclude rows with Ind_2 == 4 or 5
    (df_all_Ind1_Ind2['TimeInterval'] == 'Standard') &  # Apply only to 'Standard' intervals
    ((df_all_Ind1_Ind2['SpCond_QC0'].isna()) | (df_all_Ind1_Ind2['SpCond_QC0'] < ThrV_2)), 
    1,  # Set 'Ind_5.2' to 1 if the condition is met
    0   # Otherwise, set 'Ind_5.2' to 0
)

"""
# Saving the DataFrame
os.chdir(Results_folder)
output_path_with_index = "File_19. Ind5.2.xlsx"
df_all_Ind1_Ind2.to_excel(output_path_with_index, index=True)
print("Ind_5.2 successfully assigned based on conditions and saved to: File_19. Ind5.2.xlsx")
"""


#%%
#### 7.3.2.3. 'Ind_5.3' (Condition_III) ------------------------------------------

# Absolute calculation
df_all_Ind1_Ind2['delta_Water_DataSetClimate'] = abs(df_all_Ind1_Ind2['WaterTemp_EXO_QC0'] - df_all_Ind1_Ind2['AirTemp'])

# Step 1: Explicitly Remove Events with Ind_2 == 4, 5, or 0 Before Processing
df_filtered = df_all_Ind1_Ind2[~df_all_Ind1_Ind2['Ind_2'].isin([4, 5, 0])].copy().reset_index(drop=True)

# Step 2: Initialize New Columns in the Filtered DataFrame
df_filtered['delta_Water_DataSetClimate_avg'] = None
df_filtered['Ind_5.3'] = None

# Step 3: Initialize Variables for Event Tracking
event_start_idx = None
event_end_idx = None

# Step 4: Define Start & End Columns Based on Variable
if Variable == 'WaterTemp_EXO':
    start_column = 'StartTimeEvent'
    end_column = 'EndTimeEvent'
else:
    start_column = 'OtherStartTime'
    end_column = 'OtherEndTime'

# Step 5: Process Each Event
for i, row in df_filtered.iterrows():
    if isinstance(row[start_column], str) and 'Starting time of Event' in row[start_column]:
        event_start_idx = i

    if isinstance(row[end_column], str) and 'Ending time of Event' in row[end_column]:
        event_end_idx = i

        if event_start_idx is not None and event_end_idx is not None:
            event_range = df_filtered.loc[event_start_idx:event_end_idx]

            valid_deltas = event_range.loc[
                (event_range['TimeInterval'] == 'Standard') & 
                (pd.notnull(event_range['delta_Water_DataSetClimate']))
            ]['delta_Water_DataSetClimate']

            if not valid_deltas.empty:
                avg_delta = valid_deltas.mean()
                df_filtered.loc[event_start_idx:event_end_idx, 'delta_Water_DataSetClimate_avg'] = avg_delta
                df_filtered.loc[event_start_idx:event_end_idx, 'Ind_5.3'] = 1 if avg_delta < ThrV_3 else 0
            else:
                df_filtered.loc[event_start_idx:event_end_idx, 'delta_Water_DataSetClimate_avg'] = None
                df_filtered.loc[event_start_idx:event_end_idx, 'Ind_5.3'] = None

            event_start_idx = None
            event_end_idx = None

# Step 6: Concatenate the Updated Filtered Data with the Original Data
df_remaining = df_all_Ind1_Ind2[df_all_Ind1_Ind2['Ind_2'].isin([4, 5, 0])]

df_all_Ind1_Ind2 = pd.concat([df_remaining, df_filtered], ignore_index=True)

# Sort by 'LocalDateTime' column and reset the index
df_all_Ind1_Ind2['LocalDateTime'] = pd.to_datetime(df_all_Ind1_Ind2['LocalDateTime'])
df_all_Ind1_Ind2.sort_values(by='LocalDateTime', inplace=True)
df_all_Ind1_Ind2.reset_index(drop=True, inplace=True)

"""
# Saving:
os.chdir(Results_folder)
output_path_with_index = "File_20. Ind_5.3.xlsx"
df_all_Ind1_Ind2.to_excel(output_path_with_index, index=True)
print("Ind_5.3 successfully assigned based on conditions and saved to: File_20. Ind_5.3.xlsx")
"""

#%% 
#### 7.3.2.4. 'Ind_5.4' (Condition_IV) -----------------------------------------------

# Initialize columns with None
df_all_Ind1_Ind2['Stage_QC0_avg'] = None
df_all_Ind1_Ind2['Stage_QC0_backward'] = None
df_all_Ind1_Ind2['Stage_QC0_forward'] = None
df_all_Ind1_Ind2['delta_Stage_Backward'] = None
df_all_Ind1_Ind2['delta_Stage_Forward'] = None
df_all_Ind1_Ind2['Ind_5.4'] = None

# Initialize variables to store event indices
event_start_idx = None
event_end_idx = None

if Variable == 'WaterTemp_EXO':
    start_column = 'StartTimeEvent'
    end_column = 'EndTimeEvent'
else:
    start_column = 'OtherStartTime'
    end_column = 'OtherEndTime'

# Loop through the dataframe to detect event ranges and apply the condition
for i, row in df_all_Ind1_Ind2.iterrows():
    # Identify the start of the event
    if isinstance(row[start_column], str) and 'Starting time of Event' in row[start_column]:
        event_start_idx = i
        print(f"Event start detected at index {event_start_idx}")

    # Identify the end of the event
    if isinstance(row[end_column], str) and 'Ending time of Event' in row[end_column]:
        event_end_idx = i
        print(f"Event end detected at index {event_end_idx}")

        # Process the event if both start and end indices are found
        if event_start_idx is not None and event_end_idx is not None:
            # Calculate the average Stage_QC0 for the event range
            event_range = df_all_Ind1_Ind2.loc[event_start_idx:event_end_idx]
            valid_stage_values = event_range.loc[pd.notnull(event_range['Stage_QC0'])]['Stage_QC0']
            
            avg_stage = valid_stage_values.mean() if not valid_stage_values.empty else None
            if avg_stage is not None:
                print(f"Stage_QC0 average for event {event_start_idx} to {event_end_idx}: {avg_stage}")
                df_all_Ind1_Ind2.loc[event_start_idx:event_end_idx, 'Stage_QC0_avg'] = avg_stage

            # Calculate the average for backward range
            backward_range = df_all_Ind1_Ind2.loc[max(0, event_start_idx-n):event_start_idx-1]
            valid_backward_stage_values = backward_range.loc[
                (backward_range['TimeInterval'] == 'Standard') & 
                (pd.notnull(backward_range['Stage_QC0']))
            ]['Stage_QC0']
            
            avg_backward_stage = valid_backward_stage_values.mean() if not valid_backward_stage_values.empty else None
            if avg_backward_stage is not None:
                print(f"Backward Stage_QC0 average before event {event_start_idx}: {avg_backward_stage}")
                df_all_Ind1_Ind2.loc[event_start_idx:event_end_idx, 'Stage_QC0_backward'] = avg_backward_stage

            # Calculate the average for forward range
            forward_range = df_all_Ind1_Ind2.loc[event_end_idx+1:event_end_idx+n]
            valid_forward_stage_values = forward_range.loc[
                (forward_range['TimeInterval'] == 'Standard') & 
                (pd.notnull(forward_range['Stage_QC0']))
            ]['Stage_QC0']
            
            avg_forward_stage = valid_forward_stage_values.mean() if not valid_forward_stage_values.empty else None
            if avg_forward_stage is not None:
                print(f"Forward Stage_QC0 average after event {event_end_idx}: {avg_forward_stage}")
                df_all_Ind1_Ind2.loc[event_start_idx:event_end_idx, 'Stage_QC0_forward'] = avg_forward_stage

            # Calculate deltas only if both required values are available
            if pd.notnull(avg_stage) and pd.notnull(avg_backward_stage):
                delta_stage_backward = abs(avg_backward_stage - avg_stage)
                df_all_Ind1_Ind2.loc[event_start_idx:event_end_idx, 'delta_Stage_Backward'] = delta_stage_backward

            if pd.notnull(avg_stage) and pd.notnull(avg_forward_stage):
                delta_stage_forward = abs(avg_forward_stage - avg_stage)
                df_all_Ind1_Ind2.loc[event_start_idx:event_end_idx, 'delta_Stage_Forward'] = delta_stage_forward

            # Apply the condition for 'Ind_5.4' only if both deltas are available
            delta_stage_backward = df_all_Ind1_Ind2.loc[event_start_idx, 'delta_Stage_Backward']
            delta_stage_forward = df_all_Ind1_Ind2.loc[event_start_idx, 'delta_Stage_Forward']
            
            if pd.notnull(delta_stage_backward) and pd.notnull(delta_stage_forward):
                if delta_stage_forward > ThrV_4 and delta_stage_backward > ThrV_4:
                    df_all_Ind1_Ind2.loc[event_start_idx:event_end_idx, 'Ind_5.4'] = 1
                else:
                    df_all_Ind1_Ind2.loc[event_start_idx:event_end_idx, 'Ind_5.4'] = 0

            # Reset event indices for the next event
            event_start_idx = None
            event_end_idx = None
            
#%% 
#### 7.3.2.5. 'Ind_5' --------------------------------------------------------
df_all_Ind1_Ind2['Ind_5'] = None

# Loop through the dataframe and apply the logic for 'Ind_5'
for i, row in df_all_Ind1_Ind2.iterrows():
    # Ensure that Ind_5.1, Ind_5.2, Ind_5.3, and Ind_5.4 are not null
    if pd.notnull(row['Ind_5.1']) and pd.notnull(row['Ind_5.2']) and pd.notnull(row['Ind_5.3']) and pd.notnull(row['Ind_5.4']):
        # Check the condition for Ind_5.4 (mandatory requirement) and one of Ind_5.1, Ind_5.2, or Ind_5.3
        if row['Ind_5.4'] == 1 and (row['Ind_5.1'] == 1 or row['Ind_5.2'] == 1 or row['Ind_5.3'] == 1):
            df_all_Ind1_Ind2.at[i, 'Ind_5'] = 1  # Set 'Ind_5' to 1 if the conditions are met
        else:
            df_all_Ind1_Ind2.at[i, 'Ind_5'] = 0  # Set 'Ind_5' to 0 if conditions are not met
    else:
        df_all_Ind1_Ind2.at[i, 'Ind_5'] = None  # Leave 'Ind_5' as None if any required indicator is missing

"""
# Saving:
os.chdir(Results_folder)
output_path_with_index = "File_21. Ind_5.4 and Ind_5.xlsx"
df_all_Ind1_Ind2.to_excel(output_path_with_index, index=True)
print("Ind_5.4 and Ind_5 successfully assigned based on conditions and saved to: File_21. Ind_5.4 and Ind_5.xlsx")
"""

#%% 
### 7.3.3. 'Ind_6' (Checking/ Labelling for MNT events) ---------------------------------------------------------------------------

# Update 'Ind_6' based on 'Ind_1' values
df_all_Ind1_Ind2['Ind_6'] = np.where((df_all_Ind1_Ind2['Ind_1'] == 1), 1, 0)
print("Ind_6 successfully assigned based on conditions.")

### 7.3.4. 'Ind_7'(Checking/ Labelling for SLM events) ----------------------------------------------------------------------------

df_all_Ind1_Ind2['Ind_7'] = None

# LOGIC:
df_all_Ind1_Ind2['Ind_7'] = np.where(
    ((df_all_Ind1_Ind2['Ind_2'] == 1) | (df_all_Ind1_Ind2['Ind_2'] == 2)) & 
    (df_all_Ind1_Ind2['Ind_1'] == 0) & 
    (df_all_Ind1_Ind2['Ind_3'] == 0), 1, 0)
print("Ind_7 successfully assigned based on conditions.")

### 7.3.5. 'Ind_8' (Checking/ Labelling for PF events) ---------------------------------------------------------------------------

df_all_Ind1_Ind2['Ind_8'] = None

# Logic:
df_all_Ind1_Ind2['Ind_8'] = np.where(
    ((df_all_Ind1_Ind2['Ind_2'] == 1) | (df_all_Ind1_Ind2['Ind_2'] == 2)) & 
    (df_all_Ind1_Ind2['Ind_1'] == 0) & 
    (df_all_Ind1_Ind2['Ind_3'] == 1), 1, 0)

"""
# Saving:
os.chdir(Results_folder)
output_path_with_index = "File_22. Last version of the merged_df.xlsx"
df_all_Ind1_Ind2.to_excel(output_path_with_index, index=True)
print("Ind_8 successfully assigned based on conditions and saved to: File_22. Last version of the merged_df.xlsx")
"""

### 7.3.6. 'Ind_10' (Checking/ Labelling for 'CAL' events): ---------------------------------------------------------------------

if Variable == 'WaterTemp_EXO':
    print("\033[94mSkipping checking/ Labelling for `CAL` events (`Ind_10`), as 'Variable' is 'WaterTemp_EXO'\033[0m")
else:
    print("Proceeding with checking/ Labelling for `CAL` events (`Ind_10`)")
    
    # Initialize 'Ind_10' column with None
    df_all_Ind1_Ind2['Ind_10'] = None

    # Loop through the dataframe and apply the logic for 'Ind_10'
    for i, row in df_all_Ind1_Ind2.iterrows():
        # Ensure that Ind_2 is not null
        if pd.notnull(row['Ind_2']):
            if row['Ind_2'] == 4:
                df_all_Ind1_Ind2.at[i, 'Ind_10'] = 1 
        else:
            df_all_Ind1_Ind2.at[i, 'Ind_10'] = None  

### 7.3.7. Ind_11 (Checking/ Labelling for 'CS' events) -------------------------------------------------------------

if Variable == 'WaterTemp_EXO':
    print("\033[94mSkipping checking/ Labelling for `CS` events (`Ind_11`), as 'Variable' is 'WaterTemp_EXO'\033[0m")
else:
    print("Proceeding with checking/ Labelling for `CS` events (`Ind_11`)")

    # Initialize 'Ind_11' column with None
    df_all_Ind1_Ind2['Ind_11'] = None

    # Loop through the dataframe and apply the logic for 'Ind_11'
    for i, row in df_all_Ind1_Ind2.iterrows():
        # Ensure that 'CorrectionTypeCal' is not null
        if pd.notnull(row['CorrectionTypeCal']):
            if row['CorrectionTypeCal'] == 'CS':
                df_all_Ind1_Ind2.at[i, 'Ind_11'] = 1 
        else:
            df_all_Ind1_Ind2.at[i, 'Ind_11'] = None  

### 7.3.8. 'Ind_12' (Checking/ Labelling for 'LDC' events) --------------------------------------------------

if Variable == 'WaterTemp_EXO':
    print("\033[94mSkipping checking/ Labelling for `LDC` events (`Ind_12`), as 'Variable' is 'WaterTemp_EXO'\033[0m")
else:
    print("Proceeding with checking/ Labelling for `LDC` events (`Ind_12`)")

    df_all_Ind1_Ind2['Ind_12'] = None
    # Loop through the dataframe and apply the logic for 'Ind_12'
    for i, row in df_all_Ind1_Ind2.iterrows():
        # Ensure that `CorrectionTypeCal` is not null
        if pd.notnull(row['CorrectionTypeCal']):
            if row['CorrectionTypeCal'] == 'LDC':
                df_all_Ind1_Ind2.at[i, 'Ind_12'] = 1 
        else:
            df_all_Ind1_Ind2.at[i, 'Ind_12'] = None  

"""
# Saving:
os.chdir(Results_folder)
output_path_with_index = "File_23. Ind_6~12.xlsx"
df_all_Ind1_Ind2.to_excel(output_path_with_index, index=True)
print("Ind_6~12 successfully assigned based on conditions and saved to: File_23. Ind_6~12.xlsx")
"""


#%%
# 7.4. Final Ordering of labeling of Anomaly types #################################################################################################

def assign_label(df, Variable):
    if Variable == 'WaterTemp_EXO':
        print("\033[94mSimplified logic for 'WaterTemp_EXO' that ignores calibration events\033[0m")
        
        # Define the correct conditions for label assignment
        conditions = [
                    (df_all_Ind1_Ind2['Ind_6'] == 1)
                    #&(df_all_Ind1_Ind2['Ind_7'] == 0) &
                    #(df_all_Ind1_Ind2['Ind_8'] == 0) & 
                    #(df_all_Ind1_Ind2['Ind_5'] == 0),                              # MNT
                    ,
                        #(df_all_Ind1_Ind2['Ind_6'] == 0) & 
                        #(df_all_Ind1_Ind2['Ind_7'] == 0) & 
                        (df_all_Ind1_Ind2['Ind_8'] == 1)
                        #&(df_all_Ind1_Ind2['Ind_5'] == 0),                              # PF
                        ,
                            #(df_all_Ind1_Ind2['Ind_6'] == 0) & 
                            (df_all_Ind1_Ind2['Ind_7'] == 1)
                            #&(df_all_Ind1_Ind2['Ind_8'] == 0) & 
                            #(df_all_Ind1_Ind2['Ind_5'] == 0),                              # SLM
                            ,
                                #(df_all_Ind1_Ind2['Ind_6'] == 0) & 
                                #(df_all_Ind1_Ind2['Ind_7'] == 0) & 
                                #(df_all_Ind1_Ind2['Ind_8'] == 0) & 
                                (df_all_Ind1_Ind2['Ind_5'] == 1)                               # LWL
                                ]

        # Corresponding labels for the conditions
        labels = ['MNT', 'PF', 'SLM', 'LWL']

        # Apply the conditions to create the 'Label' column
        df_all_Ind1_Ind2['Label'] = np.where(
            df_all_Ind1_Ind2['Ind_2'].isin([1, 2, 3, 4, 5]), 
            np.select(conditions, labels, default='VIN'), 
            None
        )
       
    else:
        # Full logic for other variables
        print("Proceeding with full logic for variables")
        conditions = [
            df['Ind_10'] == 1,                              # CAL
                df['Ind_11'] == 1,                              # CS
                    df['Ind_12'] == 1,                              # LDC
                        (df['Ind_6'] == 1)
                        #& (df['Ind_7'] == 0) &
                        #(df['Ind_8'] == 0) & 
                        #(df['Ind_5'] == 0),                        # MNT 
                        ,  
                            #(df['Ind_6'] == 0) & 
                            #(df['Ind_7'] == 0) & 
                            (df['Ind_8'] == 1) 
                            #&(df['Ind_5'] == 0),                    # PF
                            ,       
                                #(df['Ind_6'] == 0) & 
                                (df['Ind_7'] == 1) 
                                #& (df['Ind_8'] == 0) & 
                                #(df['Ind_5'] == 0),                # SLM
                                ,
                                    #(df['Ind_6'] == 0) & 
                                    #(df['Ind_7'] == 0) & 
                                    #(df['Ind_8'] == 0) & 
                                    (df['Ind_5'] == 1)             # LWL
        ]

        labels = ['CAL', 'CS', 'LDC', 'MNT', 'PF', 'SLM', 'LWL']

        # Apply labels based on conditions
        df['Label'] = np.where(
            df['Ind_2'].isin([1, 2, 3, 4, 5]), 
            np.select(conditions, labels, default='VIN'), 
            None
        )

    return df

# Apply the function directly to the DataFrame
df_all_Ind1_Ind2 = assign_label(df_all_Ind1_Ind2, Variable)

# Map the labels to class numbers
df_all_Ind1_Ind2['class'] = np.select(
    [df_all_Ind1_Ind2['Label'] == label for label in ['MNT', 'CAL', 'LDC', 'CS', 'PF', 'SLM', 'LWL', 'VIN']],
    [1, 2, 3, 4, 5, 6, 7, 8])


# Check the label distribution
print("Label distribution:")
print(df_all_Ind1_Ind2['Label'].value_counts())


# Saving:
save_dir = Path(Results_folder) / Dataset_Dir
save_dir.mkdir(parents=True, exist_ok=True)
#output_path = save_dir / "File_24. Final labeling.xlsx"
output_path = save_dir / "File_1. Final labeling.csv"
df_all_Ind1_Ind2.to_csv(output_path, index=False)
print("Final labeling successfully assigned based on conditions and saved to:", output_path)

