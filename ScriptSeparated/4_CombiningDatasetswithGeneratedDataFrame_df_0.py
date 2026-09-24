#%%
# 4. Combining Datasets with Generated Data Frame (df_0) #########################################################################################

# Creating a data frame each 15 min (df_0)
df_0 = pd.date_range(start=start_date, end=end_date, freq=Time_Step_of_data)
df_0 = pd.DataFrame(df_0, columns=['LocalDateTime'])

## 4.1. Concatenating the Aquatic Raw dataset (RawAquaticDataset) to df_0 ==========================================================================
def merge_aquatic_dataset(df_0, raw_aquatic_dataset):
    """
    Merge the aquatic raw dataset with the base dataframe.
    
    Parameters:
    df_0 (DataFrame): The base dataframe with datetime index
    raw_aquatic_dataset (DataFrame): The raw aquatic dataset to merge
    
    Returns:
    DataFrame: The merged dataframe with aquatic data
    """
    # Reset the index for both datasets so 'LocalDateTime' becomes a column again
    df_0_copy = df_0.copy()
    raw_aquatic_copy = raw_aquatic_dataset.copy()
    
    df_0_copy.reset_index(inplace=True)
    raw_aquatic_copy.reset_index(inplace=True)

    # Convert 'LocalDateTime' column in both dataframes to datetime format if it's not already
    df_0_copy['LocalDateTime'] = pd.to_datetime(df_0_copy['LocalDateTime'])
    raw_aquatic_copy['LocalDateTime'] = pd.to_datetime(raw_aquatic_copy['LocalDateTime'])

    # Check for and remove duplicate timestamps in df_0_extended
    df_0_extended = df_0_copy.drop_duplicates(subset='LocalDateTime').copy()

    # Now, again set the 'LocalDateTime' column as the index for both DataFrames
    raw_aquatic_copy.set_index('LocalDateTime', inplace=True)
    df_0_copy.set_index('LocalDateTime', inplace=True)

    # Rename and add "_QC0" to the columns in RawAquaticDataset
    raw_aquatic_copy = raw_aquatic_copy.rename(columns={
        'BattVolt': 'BattVolt_QC0', 
        'EXOVolt': 'EXOVolt_QC0', 
        'ODO': 'ODO_QC0',
        'Stage': 'Stage_QC0',
        'pH': 'pH_QC0',
        'SpCond': 'SpCond_QC0',
        'WaterTemp_EXO': 'WaterTemp_EXO_QC0',
        'TurbMed': 'TurbMed_QC0'
    })

    # Initialize an empty list to store new rows
    new_rows = []

    # Loop through each row in RawAquaticDataset
    for _, row in raw_aquatic_copy.iterrows():
        # Access the index value ('LocalDateTime')
        timestamp = row.name

        # Check if 'timestamp' exists in the index of df_0
        if timestamp not in df_0_copy.index:
            # Append the timestamp to new_rows as a dictionary
            new_rows.append({'LocalDateTime': timestamp})

    # Convert new rows to a DataFrame
    new_rows_df = pd.DataFrame(new_rows)

    # Convert the 'LocalDateTime' column to a Datetime Index
    if not new_rows_df.empty:            # Ensure the DataFrame is not empty
        new_rows_df['LocalDateTime'] = pd.to_datetime(new_rows_df['LocalDateTime'])
        new_rows_df.set_index('LocalDateTime', inplace=True)

    # Using pd.concat to add the new rows to the DataFrame
    df_0_new_rows = pd.concat([df_0_copy, new_rows_df])

    # Reordering by index (LocalDateTime)
    df_0_new_rows = df_0_new_rows.sort_index()

    # Merge the RawAquaticDataset into df_0_new_rows
    merged_df = pd.merge(
        df_0_new_rows, 
        raw_aquatic_copy[['BattVolt_QC0', 'EXOVolt_QC0', 'ODO_QC0','Stage_QC0','pH_QC0','SpCond_QC0','WaterTemp_EXO_QC0','TurbMed_QC0']], 
        left_index=True, 
        right_index=True, 
        how='left'
    )

    # Drop the 'index' column if it exists
    if 'index' in merged_df.columns:
        merged_df = merged_df.drop(columns=['index'])
    
    return merged_df

# call:
merged_df = merge_aquatic_dataset(df_0, RawAquaticDataset)

merged_df.head(2)

#%%
## 4.2. Concatenating Climate Raw Dataset (DataSetClimate) to df_0 ========================================================================

def merge_climate_dataset(merged_df, dataset_climate):
    """
    Merge the climate dataset with the existing merged dataframe.
    
    Parameters:
    merged_df (DataFrame): The existing merged dataframe
    dataset_climate (DataFrame): The climate dataset to merge
    
    Returns:
    DataFrame: The updated merged dataframe with climate data
    """
    # Create a copy to avoid modifying the original dataframes
    climate_copy = dataset_climate.copy()
    merged_copy = merged_df.copy()
    
    # Replace -9999 with NaN
    climate_copy.replace(-9999, np.nan, inplace=True)

    # Initialize the 'AirTemp' column
    climate_copy['AirTemp'] = climate_copy['AirTemp_EE08_avg']

    # Merge the 'DataSetClimate' into the merged_df
    updated_merged_df = pd.merge(
        merged_copy, 
        climate_copy[['AirTemp']], 
        left_index=True, 
        right_index=True, 
        how='left'
    )
    
    return updated_merged_df

# call:
merged_df = merge_climate_dataset(merged_df, DataSetClimate)

merged_df.head(2)

#%% 
## 4.3. Concatenating Filed Note Dataset (FieldNoteDataset) to df_0 ===============================================================================

# Convert the columns to datetime format in the merged_df
merged_df = merged_df.reset_index()
merged_df['LocalDateTime'] = pd.to_datetime(merged_df['LocalDateTime'])
# Convert the columns to datetime format in the FieldNoteDataset
FieldNoteDataset = FieldNoteDataset.reset_index()
FieldNoteDataset['Begin: End time'] = pd.to_datetime(FieldNoteDataset['Begin: End time'])

# Check for and remove duplicate timestamps in "merged_df"
merged_df = merged_df.drop_duplicates(subset='LocalDateTime').copy()

# Rename 'Begin: End time' to 'LocalDateTime' in 'FieldNoteDataset'
FieldNoteDataset.rename(columns={'Begin: End time': 'LocalDateTime'}, inplace=True)

# Initialize a list to hold new rows
new_rows = []

# Check for and remove duplicate timestamps in df_0_extended
df_0_extended = df_0.drop_duplicates(subset='LocalDateTime').copy()

# Loop through each row in FieldNoteDataset
for _, row in FieldNoteDataset.iterrows():
    timestamp = row['LocalDateTime']
    if timestamp not in df_0_extended['LocalDateTime'].values:
        new_rows.append({'LocalDateTime': timestamp})

# Convert new rows to a DataFrame
new_rows_df= pd.DataFrame(new_rows)

# Add these new rows to merged_df
merged_df = pd.concat([merged_df, new_rows_df], ignore_index=True)

# Sort the dataframe by Timestamp to maintain chronological order
merged_df = merged_df.sort_values(by='LocalDateTime').reset_index(drop=True)

# Merge the additional columns from FieldNoteDataset into merged_df
merged_df = pd.merge(merged_df, FieldNoteDataset[['LocalDateTime', 'Method', 'Combined Time', 'Event Number']], on='LocalDateTime', how='left')

merged_df.head(2)

#%% 
## 4.4. Concatenating the Aquatic QC Dataset (QCDataset) to df_0 ===========================================================================

# Reset the index for both datasets. So, 'LocalDateTime' becomes a column again!
merged_df.reset_index(inplace=True)
QCDataset.reset_index(inplace=True)

# Initialize a list to hold new rows
new_rows = []
# Loop through each row in QCDataset
for _, row in QCDataset.iterrows():
    timestamp = row['LocalDateTime']
    if timestamp not in merged_df['LocalDateTime'].values:
        new_rows.append({'LocalDateTime': timestamp})
# Convert new rows to a DataFrame
new_rows_df = pd.DataFrame(new_rows)
# Add these new rows to "merged_df"
merged_df = pd.concat([merged_df, new_rows_df], ignore_index=True)
# Sort the dataframe by Timestamp to maintain chronological order
merged_df = merged_df.sort_values(by='LocalDateTime').reset_index(drop=True)
# Merge the additional columns from "QCDataset" into "merged_df"
merged_df = pd.merge(merged_df, QCDataset[['LocalDateTime', f'{Variable}_QC1', 'QualifierCode']], on='LocalDateTime', how='left')

# Drop the first column ('index') and keep 'LocalDateTime' as the index
merged_df = merged_df.drop(columns=['index'])
# Set 'LocalDateTime' as the index
merged_df.set_index('LocalDateTime', inplace=True)

