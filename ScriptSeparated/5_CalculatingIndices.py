#%% 
# 5. Calculating Indices and Defining Logics for Anomaly Identification and Categorization  ######################################################
"""
The final benchmark dataset is standardized to a 15-minute interval and includes `raw`, `QC`, and `label` columns. Because the merged Field Notes datasets
sometimes have timestamps that fall off this 15-minute grid, I added a flag with two values—`Standard` (on-grid) and `Non_Standard` (off-grid). After all
logic and labeling are applied, I drop the `Non_Standard` rows, leaving only on-grid records that contain both `raw` and `QC` data.
"""
## 5.1. Defining `Standard` and `Non_Standard` TimeInterval ===============================================================================
def define_time_interval(df, standard_minutes=[0, 15, 30, 45]):
    df_copy = df.copy()
    # Reset the index to make 'LocalDateTime' a column if it's currently the index
    if df_copy.index.name == 'LocalDateTime':
        df_copy = df_copy.reset_index()
    # Ensure 'LocalDateTime' is in datetime format
    df_copy['LocalDateTime'] = pd.to_datetime(df_copy['LocalDateTime'])
    # Create a 'TimeInterval' column to check the minutes part of the timestamp
    df_copy['TimeInterval'] = df_copy['LocalDateTime'].dt.minute.apply(
        lambda x: 'Standard' if x in standard_minutes else 'Non-standard')
    return df_copy
df_all = define_time_interval(merged_df)  

#%%
### 5.2. `AnomalyIndex` (Extracting Anomalies) ----------------------------------------------------------------------------------------

# Anomaly function: Calculating differences point-by-point
#df_all['RawQCColumn'] = abs(df_all[f'{Variable}_QC1'] - df_all[f'{Variable}_QC0'])
#df_all['AnomalyIndex'] = np.nan
def anomaly_extraction(df, variable):
    # Anomaly: Calculating differences point-by-point
    df['RawQCColumn'] = abs(df[f'{variable}_QC1'] - df[f'{variable}_QC0'])
    df['AnomalyIndex'] = np.nan
    return df
df_all = anomaly_extraction(df_all, Variable)                                   # Call the function




def calculate_anomaly_index(df, variable, time_interval_filter='Standard'):
    """
    Calculate anomaly index based on RawQC differences.
    
    Parameters:
    df (DataFrame): The dataframe to process
    variable (str): The variable name for QC columns
    time_interval_filter (str): Time interval to filter by (default: 'Standard')
    
    Returns:
    DataFrame: Updated dataframe with RawQCColumn and AnomalyIndex columns
    """
    # Anomaly: Calculating differences point-by-point
    df[f'RawQCColumn'] = abs(df[f'{variable}_QC1'] - df[f'{variable}_QC0'])
    
    # Initialize AnomalyIndex column
    df['AnomalyIndex'] = np.nan
    
    # Apply logic only to rows where TimeInterval matches the filter
    standard_mask = df['TimeInterval'] == time_interval_filter
    zero_mask = df['RawQCColumn'].eq(0)
    nan_mask = df['RawQCColumn'].isna()
    
    # For filtered TimeInterval rows:
    df.loc[standard_mask & zero_mask, 'AnomalyIndex'] = 0                           # If RawQCColumn == 0, fill AnomalyIndex with 0
    df.loc[standard_mask & ~zero_mask & ~nan_mask, 'AnomalyIndex'] = 1              # If RawQCColumn is not 0 and not NaN, fill AnomalyIndex with 1
    df.loc[standard_mask & nan_mask, 'AnomalyIndex'] = 1                            # If RawQCColumn is NaN, fill AnomalyIndex with 1
    return df

df_all = calculate_anomaly_index(df_all, Variable)

