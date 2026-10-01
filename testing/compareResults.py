import pandas as pd
import numpy as np
import numbers
import subprocess


subprocess.run("echo \"Running Ehsan's Script...\"", shell=True)
subprocess.run("cd /Users/a02523625/Documents/HorsburghRA/EhsanData && \
               python3 Script.py > /dev/null", shell=True)
subprocess.run("echo \"Running Modularized Script...\"", shell=True)
subprocess.run("cd /Users/a02523625/Documents/HorsburghRA/EhsanParsed/ScriptModularized && \
               python3 main.py > /dev/null", shell=True)
exit()


file_a = "./Results/EHSANtest1.csv"
file_b = "./Results/MEtest1.csv"

df_a = pd.read_csv(file_a)
df_b = pd.read_csv(file_b)

# Define which columns should contain the same values


# "LocalDateTime" : "LocalDateTime"
# "BattVolt_QC0" : "BattVolt"
# "EXOVolt_QC0" : "EXOVolt"
# "ODO_QC0" : "ODO"
# "Stage_QC0" : "Stage"
# "pH_QC0" : "pH"
# "SpCond_QC0" : "SpCond"
# "WaterTemp_EXO_QC0" : "WaterTemp_EXO"
# "TurbMed_QC0" : "TurbMed"
# "AirTemp" : "BattVolt"
# "Method" : "AirTemp_ST110_Avg"
# "Combined Time" : "AirTemp_EE08_avg"
# "Event Number" : "ODO_QC1"
# "ODO_QC1" : "QualifierCode"
# QualifierCode

column_mapping = {
    "BattVolt_QC0": "BattVolt",
    "EXOVolt_QC0": "EXOVolt",
    "ODO_QC0": "ODO",
    "Stage_QC0": "Stage",
    "pH_QC0": "pH",
    "SpCond_QC0": "SpCond",
    "WaterTemp_EXO_QC0": "WaterTemp_EXO",
    "TurbMed_QC0": "TurbMed",
    "AirTemp" : "AirTemp_EE08_avg",
    "ODO_QC1": "ODO_QC1",
    "QualifierCode": "QualifierCode",
    "RawQCColumn": "_ManualChangeAmt",
    "AnomalyIndex": "_IsAnomaly",
    "Ind_1": "_FieldNoteFlag",
    "Cal_Counter": "_Cal_Counter",

    # These two columns are commented out because of the way we manage our field notes differently -- I believe both programs are doing the same thing with different representations of the field notes... Cal_counter is exactly what it should be
    # "CalStartTime": "_CalStartTime",
    # "CalEndTime": "_CalEndTime"

    "iMinePrei": "_ChangeTrends"
}

# Make sure LocalDateTime is actually treated as a datetime
df_a["LocalDateTime"] = pd.to_datetime(df_a["LocalDateTime"])
df_b["LocalDateTime"] = pd.to_datetime(df_b["LocalDateTime"])

# Find timestamps that exist in BOTH files
common_times = df_a["LocalDateTime"].isin(df_b["LocalDateTime"])

# Keep only rows from File A whose timestamps exist in File B
df_a_common = df_a[common_times]

# Keep only rows from File B whose timestamps exist in File A
df_b_common = df_b[
    df_b["LocalDateTime"].isin(df_a["LocalDateTime"])
]

# Set LocalDateTime as the index so matching happens by timestamp
df_a_common = df_a_common.set_index("LocalDateTime")
df_b_common = df_b_common.set_index("LocalDateTime")

# Compare each pair of columns
for col_a, col_b in column_mapping.items():

    if col_a not in df_a_common.columns:
        print(f"ERROR: '{col_a}' not found in File A")
        continue

    if col_b not in df_b_common.columns:
        print(f"ERROR: '{col_b}' not found in File B")
        continue

    # Align the two columns using LocalDateTime
    is_numeric_a = pd.api.types.is_numeric_dtype(df_a_common[col_a]) and not pd.api.types.is_bool_dtype(df_a_common[col_a])
    is_numeric_b = pd.api.types.is_numeric_dtype(df_b_common[col_b]) and not pd.api.types.is_bool_dtype(df_b_common[col_b])

    if not is_numeric_a and not is_numeric_b:
        comparison = ((df_a_common[col_a] == df_b_common[col_b]) | (df_a_common[col_a].isna() & df_b_common[col_b].isna()))
    else:
        comparison = np.isclose(
            df_a_common[col_a],
            df_b_common[col_b],
            atol=0.001,
            equal_nan=True
        )
        comparison = pd.Series(comparison, index=df_a_common.index)


    differences = comparison[~comparison]

    if len(differences) == 0:
        print(f"\033[92m✓ {col_a} matches {col_b}\033[0m")
    else:
        print(f"\033[91m✗ {col_a} does NOT match {col_b}\033[0m")
        print(f"  Number of differences: {len(differences)}")

        for timestamp in differences.index:
            print(
                f"  {timestamp}[{col_a}/{col_b}]: "
                f"File A = {df_a_common.loc[timestamp, col_a]}, "
                f"File B = {df_b_common.loc[timestamp, col_b]}"
            )