import numpy as np
import pandas as pd
import re

class AnomalyExtractor:
    def __init__(self, dataManager, verbose=True):
        if verbose: print(" -- Anomaly Extraction --")
        self.dataManager = dataManager
        self.dataframe = dataManager.get_main()
        self.variable_of_interest = dataManager.settings.settings["Variable"]
        self.verbose = verbose

    """
    Each Method in this class follows the steps given in Ehsan's paper. The sections listed above each method correspond to the section numbers in the paper where the method is described. The paper can be found here: https://drive.google.com/file/d/1D81HE6KTDQp2VLNVsigTh60mVpd6u5PM/view?usp=sharing

    I have changed the names of the columns from the original paper (because the original names were confusing). Preceeding underscores have been added to the names to denote these are analysis columns, not data columns. The key is given below:
     - RawQCColumn -> _ManualChangeAmt
     - AnomalyIndex -> _IsAnomaly
     - Ind_1 -> _fieldNoteFlag
     - Cal_Counter -> _Cal_Counter
     - CalStartTime -> _CalStartTime
     - CalEndTime -> _CalEndTime
     - iMinePrei -> _ChangeTrends

    """

    # Section 3.2.2 
    # Checks to see if there is a difference between our manually changed (QC'ed) data and the raw value we found -- in other words, was this data point manually changed. Adds "_ManualChangeAmt" column which has how far off these values are from each other, as well as a True/False flag in the "_IsAnomaly" column
    def point_by_point_difference(self):
        if self.verbose: print("Calculating Point-by-Point Differences...")
        qc_col = f'{self.variable_of_interest}_QC1'
        raw_col = f'{self.variable_of_interest}'

        # These columns are titled "RawQCColumn" and "AnomalyIndex" in Ehsan's paper -— I think those names are confusing so I changed them
        self.dataframe['_ManualChangeAmt'] = abs(self.dataframe[qc_col] - self.dataframe[raw_col])
        self.dataframe['_IsAnomaly'] = (self.dataframe[qc_col] != self.dataframe[raw_col])

    # Section 3.2.3
    # Checks against all the field notes and labels each row with a flag whether or not there was a field visit going on at the time of this data being gathered. 
    # This function is equivilant to update_ind1_based_on_events() in Ehsan's paper (which is an absolutely awful name -- I tried to improve it to have anything to do with what the function was actually doing.)
    # - Adds a new column to the main dataset (get_main) in out DataManger object called _fieldNoteFlag
    # - this _fieldNoteFlag (equivilant to ind_1) is set to 
    #    - 0 for rows that are outside any field visit
    #    - 1 for any rows that occur during a regular site visit
    #    - 2 for any rows that occur during a visit where calibration keywords (from the YAML config) appear in the ‘Method’ column text of the field notes. 
    def check_field_notes(self):
        if self.verbose: print("Checking Field Notes...")
        fieldNotes = self.dataManager.fieldNotes
        fieldNotes["BeginTime"] = pd.to_datetime(fieldNotes["BeginTime"])
        fieldNotes["EndTime"] = pd.to_datetime(fieldNotes["EndTime"])
        
        # Main dataframe timestamps
        timestamps = self.dataframe.index
        calibration_list_regex =  "|".join(map(re.escape, self.dataManager.settings.settings["CalibrationList"]))
        
        flags = []

        for timestamp in timestamps:
            # Find all fieldNotes that contain this timestamp
            matching_notes = fieldNotes[(fieldNotes["BeginTime"] <= timestamp) & (fieldNotes["EndTime"] >= timestamp)]

            # There was no field Visit during this data point
            if matching_notes.empty:
                flags.append(0)
                continue

            # Check for matching calibration keywords
            is_calibration = matching_notes["Method"].fillna("").str.contains(calibration_list_regex, case=False, regex=True).any()
            if is_calibration: flags.append(2)
            else: flags.append(1)

        # For calibration, identification is ignored for water temperature by design because for the sensors used in this study water temperature is not calibrated in the field. The value of this field is set to 1 for all temperature rows that occur during a site visit
        if self.variable_of_interest == "T":
            flags = [1 if x == 2 else x for x in flags]

        # Now we have assembled the column, we need to concatenate it
        self.dataframe["_fieldNoteFlag"] = flags

    # Section 3.2.3
    # This function is run to specifically identify calibration events, their numbering, start time, and end time. Since the next function assesses the ranges of the time series that are affected by the calibration events, knowing the calibration event numbers is useful. This function scans the ’_fieldNoteFlag’ column in self.dataframe to find contiguous calibration windows (‘_fieldNoteFlag = 2’), numbers them in order, and annotates their start and end rows, adding new columns called ‘Cal_Counter’, ‘CalStartTime’, and ‘CalEndTime’. If the variable is water temperature, this function is skipped.
    def process_calibration_events(self):
        if self.verbose: print("Processing Calibration Events...")
        if self.variable_of_interest == "WaterTemp_EXO": return

        # Initialize the calibration counter and lists for annotations
        cal_counter = 0
        cal_counter_list = []
        cal_start_annotations = [None] * len(self.dataframe)
        cal_end_annotations = [None] * len(self.dataframe)
        
        # Flag to track if inside a calibration event
        inside_event = False

        # Iterate through each row in the DataFrame
        for i in range(len(self.dataframe)):
            if self.dataframe.iloc[i]['_fieldNoteFlag'] == 2: # If it's a calibration event
                if not inside_event:
                    # Entering a new calibration event
                    cal_counter += 1
                    inside_event = True
                    cal_start_annotations[i] = f'Starting time of CalB{cal_counter}'
                
                # Add the current calibration number to the counter list
                cal_counter_list.append(cal_counter)
                
                # Check if it's the end of the calibration event (next row is not a calibration event)
                if i + 1 < len(self.dataframe) and self.dataframe.iloc[i + 1]['_fieldNoteFlag'] != 2:
                    cal_end_annotations[i] = f'Ending time of CalN{cal_counter}'
                    inside_event = False  # Exit the calibration event
            else:
                # Outside of a calibration event
                cal_counter_list.append(0)
                inside_event = False

        # Add the annotations to the DataFrame
        self.dataframe['_Cal_Counter'] = cal_counter_list
        self.dataframe['_CalStartTime'] = cal_start_annotations
        self.dataframe['_CalEndTime'] = cal_end_annotations

    # Section 3.2.3
    # After calibration events are processed, the script then identifies ranges of data points that are affected by each calibration as a third step. This step detects periods outside of the calibration windows (the time period when the field crew was actually at the station) that are likely influenced by the calibration performed by the field crew. The deviation between raw and QC data (‘RawQCColumn’) and its time-step-to-time-step change (calculated in a column called ‘iMinePrei’) is analyzed. For non–water temperature variables, each timestamp with ‘Ind_1 = 0’ is labeled as ‘CS’ for “constant shift” and saved in a new column called ‘CorrectionTypeCal’ when the deviation is nonzero (‘RawQCColumn’ ≠ 0) and flat (‘iMinePrei = 0’). Timestamps are labeled as‘LDC’ for “linear drift correction” and saved in the ‘CorrectionTypeCal’ column whenthe deviation is nonzero and changing (‘iMinePrei’ ≠ 0). Consecutive labeled rows aregrouped into a new column called ‘AffectedbyCal’ events, each assigned an incrementingID called ‘AffectedbyCal_Counter’, with start/end markers added in new columns in thedata frame called ‘AffectedCalStartTime’ and ‘AffectedCalEndTime’, respectively.
    def calculate_manual_change_trends(self):
        if self.verbose: print("Calculating Manual Change Trends...")
        self.dataframe['_ChangeTrends'] = self.dataframe['_ManualChangeAmt'].diff()
        self.dataframe = self.dataframe.reset_index(drop=False)
        self.dataframe['_CorrectionTypeCal'] = self.dataframe.apply(AnomalyExtractor.classify_calibration_row, axis=1)

        # Propagate classification to the previous row
        for i in range(1, len(self.dataframe)):
            if self.dataframe.at[i, '_CorrectionTypeCal'] in ['CS', 'LDC']:
                self.dataframe.at[i - 1, '_CorrectionTypeCal'] = self.dataframe.at[i, '_CorrectionTypeCal']

        # self.dataframe[(self.dataframe.index.month == 7) & (self.dataframe.index.day == 31)].to_csv("../my_output_folder/combinedData.csv")
        self.dataframe[(self.dataframe['_IsAnomaly']) == True].to_csv("../my_output_folder/combinedData.csv")



    """
    Helper Functions
    """
    # Checks if x is a valid numeric value (not 0, not NaN, and not -9999).
    @staticmethod
    def is_valid_numeric(x):
        try:
            if pd.isna(x):
                return False
            x_float = float(x)
            if x_float == 0 or x_float == -9999:
                return False
            return True
        except Exception:
            return False

    # Classifies each row into 'CS' or 'LDC'.
    @staticmethod
    def classify_calibration_row(row):
        if row['_fieldNoteFlag'] == 0:
            # This data wasn't taken during a field visit
            if row['_ChangeTrends'] == 0 and AnomalyExtractor.is_valid_numeric(row['_ManualChangeAmt']): 
                # This data 
                return 'CS'
            elif AnomalyExtractor.is_valid_numeric(row['_ChangeTrends']) and AnomalyExtractor.is_valid_numeric(row['_ManualChangeAmt']):
                return 'LDC'
        return None
        
