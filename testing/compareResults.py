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

        "AffectedCalStartTime2": "_AnomalyEventStart",
        "AffectedCalEndTime2": "_AnomalyEventEnd",
        "RepeatedEvent": "_RepeatedEvent",
        "Spike": "_SpikeDetected",
        "AnomalyPattern": "_AnomalyPattern"
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

        # Align the two columns using LocalDateTime
        is_numeric_a = pd.api.types.is_numeric_dtype(df_a_common[col_a]) and not pd.api.types.is_bool_dtype(df_a_common[col_a])
        is_numeric_b = pd.api.types.is_numeric_dtype(df_b_common[col_b]) and not pd.api.types.is_bool_dtype(df_b_common[col_b])

        if not is_numeric_a and not is_numeric_b:
            comparison = ((df_a_common[col_a] == df_b_common[col_b]) | (df_a_common[col_a].isna() & df_b_common[col_b].isna()))
        else:
            comparison = np.isclose(
                df_a_common[col_a],
                df_b_common[col_b],
                atol=0.00001,
                equal_nan=True
            )
            comparison = pd.Series(comparison, index=df_a_common.index)

        differences = comparison[~comparison]

        if len(differences) == 0:
            if self.verbose: print(f"\033[92m✓ {col_a} matches {col_b}\033[0m")
            return True
        else:
            if not self.verbose:
                return False
            print(f"\033[91m✗ {col_a} does NOT match {col_b}\033[0m")
            print(f"  Number of differences: {len(differences)}")

            max_display = 50
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
    config = Configuration('ODO', 'LR_Mendon_AA', 'LR_GC_C', 2022)

    must_run_scripts = bool(int(sys.argv[1]))
    if must_run_scripts:
        # print(">>> Running Ehsan's Script...")
        # subprocess.run("cd /Users/a02523625/Documents/HorsburghRA/EhsanData && \
        #             python3 Script.py EHSAN.csv > /dev/null 2>&1", shell=True)
        print(">>> Running Modularized Script...")
        processor = SingleProcessor(config, verbose=True)
        processor.preprocess()
        processor.anomaly_extraction()
        output_path = f"{output_folder}/ME.csv"
        processor.export_data(output_path)
        config.output = output_path

    else:
        print("Skipping script execution.")

    file_a = config.get_compare_to_file()
    file_b = "../_test_results/ME.csv"

    subprocess.run(f"cd /Users/a02523625/Documents/HorsburghRA/EhsanParsed/testing && \
                python3 csvAnalyzer.py \"{file_b}\" ../_test_results/ME_Parsed.csv _IsAnomaly > /dev/null 2>&1", shell=True)
    subprocess.run(f"cd /Users/a02523625/Documents/HorsburghRA/EhsanParsed/testing && \
                python3 csvAnalyzer.py \"{file_a}\" ../_test_results/EHSAN_Parsed.csv AnomalyIndex > /dev/null 2>&1", shell=True)

    print("\n -- Comparison -- \n")
    print(config)

    com = CompareCsvDataframes(file_a, file_b, verbose=True)
    com.compare()

