import sys
from pathlib import Path
# Add the parent folder to Python's import path
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))


import pandas as pd
import numpy as np
import numbers
import subprocess

from ScriptModularized.singleProcessor import Configuration, SingleProcessor


class CompareCsvDataframes:
    def __init__(self, df_1_filepath, df_2_filepath, verbose=False):
        self.df_1 = pd.read_csv(df_1_filepath, low_memory=False)
        self.df_2 = pd.read_csv(df_2_filepath, low_memory=False)
        self.verbose = verbose

    def compare(self):
        com = CompareDataframes(self.df_1, self.df_2, verbose=self.verbose)
        return com.compare()


class CompareDataframes:
    COLUMN_MAPPING = {
        # "BattVolt_QC0": "BattVolt",
        # "EXOVolt_QC0": "EXOVolt",
        # "ODO_QC0": "ODO",
        # "Stage_QC0": "Stage",
        # "pH_QC0": "pH",
        # "SpCond_QC0": "SpCond",
        # "WaterTemp_EXO_QC0": "WaterTemp_EXO",
        # "TurbMed_QC0": "TurbMed",
        # "AirTemp" : "AirTemp_EE08_avg",
        # "ODO_QC1": "ODO_QC1",
        # "QualifierCode": "QualifierCode",
        "RawQCColumn": "_ManualChangeAmt",
        "AnomalyIndex": "_IsAnomaly",
        "Ind_1": "_FieldNoteFlag",
        # "Cal_Counter": "_Cal_Counter",

        "iMinePrei": "_ChangeTrends",
        "CorrectionTypeCal": "_CorrectionTypeCal",
        "AffectedbyCal_Counter": "_CalibrationGroup",
        # "AffectedCalStartTime": "_CalibrationStart",
        # "AffectedCalEndTime": "_CalibrationEnd"
        "Ind_2": "_AnomalyType",
        "Event_Counter": "_AnomalyEventNumber",
        "StartTimeEvent": "_StartTimeEvent",
        "EndTimeEvent": "_EndTimeEvent",
        "OtherStartTime": "_OtherStartTime",
        "OtherEndTime": "_OtherEndTime",

        "AffectedCalStartTime2": "_AnomalyEventStart",
        "AffectedCalEndTime2": "_AnomalyEventEnd",
        "RepeatedEvent": "_RepeatedEvent",
        "Spike": "_SpikeDetected",
        "AnomalyPattern": "_AnomalyPattern",
        'EventType': 'EventType',
        "Ind_3": "Ind_3", 
        "Ind_4": "Ind_4", 
        "Ind_4": "Ind_4", 
        
        "delta_Start": "delta_Start",
        "delta_End": "delta_End",
        "Ind_5.1": "Ind_5.1",
        
        "Ind_5.2": "Ind_5.2",
        
        "delta_Water_DataSetClimate": "delta_Water_DataSetClimate",
        "delta_Water_DataSetClimate_avg": "delta_Water_DataSetClimate_avg",
        "Ind_5.3": "Ind_5.3",
        
        "Stage_QC0_avg": "Stage_avg",
        "Stage_QC0_backward": "Stage_backward",
        "Stage_QC0_forward": "Stage_forward",
        "delta_Stage_Backward": "delta_Stage_Backward",
        "delta_Stage_Forward": "delta_Stage_Forward",
        "Ind_5.4": "Ind_5.4",
    }

    def __init__(self, df_a, df_b, verbose=False):
        self.df_a = df_a
        self.df_b = df_b
        self.verbose = verbose

    def compare_col(self, df_a_common, df_b_common, col_a, col_b):
        if col_b not in df_b_common.columns:
            if self.verbose: print(f"ERROR: '{col_b}' not found in File B")
            return -1

        if col_a not in df_a_common.columns:
            if self.verbose: print(f"ERROR: '{col_a}' not found in File A")
            return -1

        # Determine whether either column has a numeric dtype
        is_numeric_a = (pd.api.types.is_numeric_dtype(df_a_common[col_a]) and not pd.api.types.is_bool_dtype(df_a_common[col_a]))
        is_numeric_b = (pd.api.types.is_numeric_dtype(df_b_common[col_b]) and not pd.api.types.is_bool_dtype(df_b_common[col_b]))

        if not is_numeric_a and not is_numeric_b:
            # Compare non-numeric columns, treating two missing values as equal
            comparison = ((df_a_common[col_a] == df_b_common[col_b]) | (df_a_common[col_a].isna() & df_b_common[col_b].isna()))
        else:
            # Convert both columns to numeric before comparing
            a = pd.to_numeric(df_a_common[col_a], errors='coerce')
            b = pd.to_numeric(df_b_common[col_b], errors='coerce')

            # Identify values that failed numeric conversion
            invalid_a = df_a_common[col_a].notna() & a.isna()
            invalid_b = df_b_common[col_b].notna() & b.isna()

            # Compare numeric values, allowing a small tolerance
            comparison = pd.Series(np.isclose(a, b, atol=0.00001, equal_nan=True), index=df_a_common.index)

            # Do not silently treat invalid strings as matching NaN values
            comparison.loc[invalid_a | invalid_b] = False

        differences = comparison[~comparison]

        if len(differences) == 0:
            if self.verbose: print(f"\033[92m✓ {col_a} matches {col_b}\033[0m")
            return True
        else:
            if not self.verbose:
                return False
            print(f"\033[91m✗ {col_a} does NOT match {col_b}\033[0m")
            print(f"  Number of differences: {len(differences)}")

            max_display = 10
            if len(differences) > max_display: 
                print(f"\033[91m  Too many differences to display (>{max_display}). Showing first {max_display} only.\033[0m")
                differences = differences[:max_display]

            for timestamp in differences.index:
                print(
                    f"  {timestamp}[{col_a}/{col_b}]: "
                    f"File A = {df_a_common.loc[timestamp, col_a]}, "
                    f"File B = {df_b_common.loc[timestamp, col_b]}"
                )
            return False

    def compare(self):

        # Make sure LocalDateTime is actually treated as a datetime
        self.df_a["LocalDateTime"] = pd.to_datetime(self.df_a["LocalDateTime"])
        self.df_b["LocalDateTime"] = pd.to_datetime(self.df_b["LocalDateTime"])

        # Find timestamps that exist in BOTH files
        common_times = self.df_a["LocalDateTime"].isin(self.df_b["LocalDateTime"])

        # Keep only rows from File A whose timestamps exist in File B
        df_a_common = self.df_a[common_times]

        # Keep only rows from File B whose timestamps exist in File A
        df_b_common = self.df_b[
            self.df_b["LocalDateTime"].isin(self.df_a["LocalDateTime"])
        ]

        # Set LocalDateTime as the index so matching happens by timestamp
        df_a_common = df_a_common.set_index("LocalDateTime")
        df_b_common = df_b_common.set_index("LocalDateTime")
        df_a_common = df_a_common[df_a_common.index.minute % 15 == 0]
        df_b_common = df_b_common[df_b_common.index.minute % 15 == 0]

        results = []

        # Compare each pair of columns
        for col_a, col_b in CompareDataframes.COLUMN_MAPPING.items():
            result = self.compare_col(df_a_common, df_b_common, col_a, col_b)
            results.append(result)
            if result == -1:
                pass # This is when we were not able to do a comparison

        return not (False in results)


if __name__ == '__main__':
    output_folder = "../_test_results"
    config = Configuration('ODO', 'LR_TG_BA', 2023)

    must_run_scripts = int(sys.argv[1])
    if must_run_scripts >= 2:
        print(">>> Running Ehsan's Script...")
        subprocess.run("cd /Users/a02523625/Documents/HorsburghRA/EhsanData && \
                    python3 Script.py EHSAN.csv > /dev/null 2>&1", shell=True)
    if must_run_scripts >= 1:
        print(">>> Running Modularized Script...")
        processor = SingleProcessor(config, verbose=True)
        processor.preprocess()
        processor.anomaly_extraction()
        output_path = config.get_output_file()
        processor.export_data(output_path)
        config.output = output_path
    if must_run_scripts == 0:
        print("Skipping script execution.")

    file_a = config.get_compare_to_file()
    file_b = config.get_output_file()
    # file_a = "../_test_results/EHSAN.csv"
    # file_b = "../_test_results/ME.csv"

    subprocess.run(f"cd /Users/a02523625/Documents/HorsburghRA/EhsanParsed/testing && \
                python3 csvAnalyzer.py \"{file_b}\" ../_test_results/ME_Parsed.csv _IsAnomaly > /dev/null 2>&1", shell=True)
    subprocess.run(f"cd /Users/a02523625/Documents/HorsburghRA/EhsanParsed/testing && \
                python3 csvAnalyzer.py \"{file_a}\" ../_test_results/EHSAN_Parsed.csv AnomalyIndex > /dev/null 2>&1", shell=True)

    print("\n -- Comparison -- \n")
    print(config)

    com = CompareCsvDataframes(file_a, file_b, verbose=True)
    com.compare()

