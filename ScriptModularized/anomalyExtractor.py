import numpy as np
import pandas as pd
import re

class AnomalyExtractor:
    def __init__(self, dataManager, verbose=True):
        if verbose: print("\033[92m -- Anomaly Extraction -- \033[0m")
        self.dataManager = dataManager
        self.dataframe = dataManager.get_main()
        self.variable_of_interest = dataManager.settings.settings["Variable"]
        self.verbose = verbose

    """
    Each Method in this class follows the steps given in Ehsan's paper. The sections listed above each method correspond to the section numbers in the paper where the method is described. The paper can be found here: https://drive.google.com/file/d/1D81HE6KTDQp2VLNVsigTh60mVpd6u5PM/view?usp=sharing

    I have changed the names of the columns from the original paper (because the original names were confusing). Preceeding underscores have been added to the names to denote these are analysis columns, not data columns. The key is given below:
     - RawQCColumn -> _ManualChangeAmt
     - AnomalyIndex -> _IsAnomaly
     - Ind_1 -> _FieldNoteFlag
     - Cal_Counter -> _Cal_Counter
     - CalStartTime -> _CalStartTime
     - CalEndTime -> _CalEndTime
     - iMinePrei -> _ChangeTrends
    """

    ######## 

    """
    Section 3.2.2 
    Checks to see if there is a difference between our manually changed (QC'ed) data and the raw value we found -- in other words, was this data point manually changed. Adds "_ManualChangeAmt" column which has how far off these values are from each other, as well as a True/False flag in the "_IsAnomaly" column
    """
    def point_by_point_difference(self):
        if self.verbose: print("Calculating Point-by-Point Differences...")
        qc_col = f'{self.variable_of_interest}_QC1'
        raw_col = f'{self.variable_of_interest}'

        # These columns are titled "RawQCColumn" and "AnomalyIndex" in Ehsan's paper -— I think those names are confusing so I changed them
        self.dataframe['_ManualChangeAmt'] = self.dataframe[qc_col] - self.dataframe[raw_col]
        self.dataframe['_IsAnomaly'] = (self.dataframe[qc_col] != self.dataframe[raw_col])

    """
    Section 3.2.3
    Checks against all the field notes and labels each row with a flag whether or not there was a field visit going on at the time of this data being gathered. 
    This function is equivilant to update_ind1_based_on_events() in Ehsan's paper (which is an absolutely awful name -- I tried to improve it to have anything to do with what the function was actually doing.)
    There was an error in Ehsan's code -- his code did not ever produce a 1 -- every value in this column was either 0 or 2. To get his exact results, you'll need to adjust the logic to always appending 2 to the flags array.
    - Adds a new column to the main dataset (get_main) in out DataManger object called _FieldNoteFlag
    - this _FieldNoteFlag (equivilant to ind_1) is set to 
       - 0 for rows that are outside any field visit
       - 1 for any rows that occur during a regular site visit
       - 2 for any rows that occur during a visit where calibration keywords (from the YAML config) appear in the 'Method' column text of the field notes. 
    """
    def check_field_notes(self):
        if self.verbose: print("Checking Field Notes...")
        fieldNotes = self.dataManager.fieldNotes
        fieldNotes["BeginTime"] = pd.to_datetime(fieldNotes["BeginTime"])
        fieldNotes["EndTime"] = pd.to_datetime(fieldNotes["EndTime"])
        
        # Main dataframe timestamps
        timestamps = self.dataframe.index
        calibration_list = self.dataManager.settings.settings["CalibrationList"]
        calibration_list_regex = r'\b(?:' + '|'.join(re.escape(keyword) for keyword in calibration_list) + r')\b'
        
        flags = []

        for timestamp in timestamps:
            # Find all fieldNotes that contain this timestamp
            matching_notes = fieldNotes[(fieldNotes["BeginTime"] <= timestamp) & (fieldNotes["EndTime"] >= timestamp)]

            # There was no field Visit during this data point
            if matching_notes.empty:
                flags.append(0)
                continue

            # Check for matching calibration keywords
            contains_calib_words = matching_notes["Method"].fillna("").str.contains(calibration_list_regex, regex=True, case=False)

            if contains_calib_words.any():
                flags.append(2)
            else:
                flags.append(2) # should be 1

        # For calibration, identification is ignored for water temperature by design because for the sensors used in this study water temperature is not calibrated in the field. The value of this field is set to 1 for all temperature rows that occur during a site visit
        if self.variable_of_interest == "WaterTemp_EXO":
            flags = [1 if x == 2 else x for x in flags]

        # Now we have assembled the column, we need to concatenate it
        self.dataframe["_FieldNoteFlag"] = flags

    """
    Section 3.2.3
    This function is run to specifically identify calibration events, their numbering, start time, and end time. Since the next function assesses the ranges of the time series that are affected by the calibration events, knowing the calibration event numbers is useful. This function scans the '_FieldNoteFlag' column in self.dataframe to find contiguous calibration windows ('_FieldNoteFlag = 2'), numbers them in order, and annotates their start and end rows, adding new columns called 'Cal_Counter', 'CalStartTime', and 'CalEndTime'. If the variable is water temperature, this function is skipped.
    """
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
            if self.dataframe.iloc[i]['_FieldNoteFlag'] == 2: # If it's a calibration event
                if not inside_event:
                    # Entering a new calibration event
                    cal_counter += 1
                    inside_event = True
                    cal_start_annotations[i] = f'Starting time of CalB{cal_counter}'
                
                # Add the current calibration number to the counter list
                cal_counter_list.append(cal_counter)
                
                # Check if it's the end of the calibration event (next row is not a calibration event)
                if i + 1 < len(self.dataframe) and self.dataframe.iloc[i + 1]['_FieldNoteFlag'] != 2:
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

    """
    Section 3.2.3
    After calibration events are processed, we must identify ranges of data points that are affected by each calibration. This step detects periods outside of the calibration windows (the time period when the field crew was actually at the station) that are likely influenced by the calibration performed by the field crew. The deviation between raw and QC data ('_ManualChangeAmt') and its time-step-to-time-step change (calculated in a column called '_ChangeTrends') is analyzed. For non-water temperature variables, each timestamp with '_FieldNoteFlag = 0' is labeled as 'CS' for “constant shift” and saved in a new column called '_CorrectionTypeCal' when the deviation is nonzero ('_ManualChangeAmt' ≠ 0) and flat ('_ChangeTrends = 0'). Timestamps are labeled as 'LDC' for “linear drift correction” and saved in the '_CorrectionTypeCal' column whenthe deviation is nonzero and changing ('_ChangeTrends ≠ 0'). Consecutive labeled rows aregrouped into a new column called 'AffectedbyCal' events, each assigned an incrementingID called '_CalibrationGroup', with start/end markers added in new columns in the dataframe called '_CalibrationStart' and '_CalibrationEnd', respectively.
    """
    def calculate_manual_change_trends(self):
        if self.verbose: print("Calculating Manual Change Trends...")

        self.dataframe['_ChangeTrends'] = self.dataframe['_ManualChangeAmt'].diff()
        self.dataframe['_CorrectionTypeCal'] = self.dataframe.apply(AnomalyExtractor.classify_calibration_row, axis=1)

        # Propagate classification to the previous row
        for i in range(1, len(self.dataframe)):
            if self.dataframe.iloc[i]['_CorrectionTypeCal'] in ['CS', 'LDC']:
                # self.dataframe.iloc[i - 1]['_CorrectionTypeCal'] = self.dataframe.iloc[i]['_CorrectionTypeCal']
                self.dataframe.loc[self.dataframe.index[i - 1], '_CorrectionTypeCal'] = self.dataframe.loc[self.dataframe.index[i], '_CorrectionTypeCal']

        #####
        self.dataframe = self.dataframe.reset_index(drop=False)
        self.dataframe['_CalibrationGroup'] = 0
        counter = 0
        propagate = False

        for i in range(len(self.dataframe)):
            if pd.notna(self.dataframe.iloc[i]['_CorrectionTypeCal']):
                if not propagate:
                    counter += 1
                self.dataframe.at[i, '_CalibrationGroup'] = counter
                propagate = True
            else:
                propagate = False

        #####
        self.dataframe['_CalibrationStart'] = None
        self.dataframe['_CalibrationEnd'] = None

        affected_groups = self.dataframe['_CalibrationGroup'].unique()
        affected_groups = [g for g in affected_groups if g != 0]

        for group in affected_groups:
            group_rows = self.dataframe[self.dataframe['_CalibrationGroup'] == group]
            if not group_rows.empty:
                start_index = group_rows.index[0]
                end_index = group_rows.index[-1]
                self.dataframe.at[start_index, '_CalibrationStart'] = group
                self.dataframe.at[end_index, '_CalibrationEnd'] = group

        #####
        affected_df = self.dataframe[self.dataframe['_CalibrationGroup'] > 0]
        
        affected_events = affected_df.groupby('_CalibrationGroup').agg({
            '_CalibrationStart': 'first',
            '_CalibrationEnd': 'first',
            '_CorrectionTypeCal': lambda x: ', '.join(map(str, x.unique()))}).reset_index()

        # For every _CalibrationStart in affected_events, find the row in self.dataframe with the same _CalibrationStart, grab that row's LocalDateTime, and put it in affected_events['Start time']
        affected_events['Start time'] = affected_events['_CalibrationStart'].map(
            lambda x: self.dataframe.loc[self.dataframe['_CalibrationStart'] == x].index[0]
            if pd.notna(x) else None)

        affected_events['End time'] = affected_events['_CalibrationEnd'].map(
            lambda x: self.dataframe.loc[self.dataframe['_CalibrationEnd'] == x].index[0] 
            if pd.notna(x) else None)

        affected_events.rename(columns={'_CorrectionTypeCal': 'Correction Type'}, inplace=True)
        affected_events = affected_events[['Start time', 'End time', 'Correction Type', '_CalibrationGroup']]

        # Update the main dataframe in the data manager with the modified dataframe.

        self.dataframe = self.dataframe.set_index('LocalDateTime')
        self.dataManager.set_main(self.dataframe)

    """
    Section 3.2.3
    As a fifth step, a function called 'assign_anomaly_types()' is run to flag anomaly events based on different roles to differentiate various patterns. This step defines a column called '_AnomalyType' and assigns a per-row status code by combining site visit flags, calibration periods, and missing data. The class dictionary assigned to the '_AnomalyType' column, is 0, 1, 2, 3, 4, or 5.
    For non-water temperature variables: 
       0 means no discrepancy ('_ManuallyCorrected = 0')
       1 means the raw data value is missing/invalid (raw data value = NaN/-9999)
       2 is the default anomaly/other
       3 means the manually corrected QC data value is missing/invalid (QC value = NaN/-9999)
       4 marks rows during a calibration visit ('Ind_1=2'), 
       5 marks rows affected by calibration afterward ('CorrectionTypeCal'= either 'CS' or 'LDC')
    For water temperature, calibration is ignored, and the codes reduce to: 
       0 for no anomaly
       1 for raw data missing
       2 for all other cases
       3 for QC missing
    """
    def assign_anomaly_types(self):
        if self.verbose: print("Assigning Anomaly Types...")
        self.dataframe['_AnomalyType'] = self.dataframe.apply(
            AnomalyExtractor.assign_anomaly_type, axis=1, args=(self.variable_of_interest,)
        )

    """
    Section 3.2.3
    The sixth step in anomaly pattern analysis is to count events. After identifying the different patterns associated with anomaly events, this step counts the number of events and saves a number for each event in a new column called '_AnomalyEventNumber'. It turns the per-row '_AnomalyType' labels into numbered events. Scanning down the 'LocalDateTime' column, any contiguous run of event codes increments an '_AnomalyEventNumber' and assigns that ID to all rows in the run (non-event rows get 0).
    """
    def extract_events(self):
        if self.verbose: print("Extracting Events...")

        event_counter = 0
        event_counter_list = []
        inside_event = False  # Flag to track if we're inside an event
        previous_anomaly_type = None  # Store previous row's _AnomalyType value

        for ind in self.dataframe['_AnomalyType']:
            # Check if it's an event - Note this works for both WaterTemp and non-WaterTemp variables. WaterTemp will never give a 4 or 5 for the _AnomalyType, but it will always be included in this list
            if ind in [1, 2, 3, 4, 5]:
                if not inside_event or (previous_anomaly_type is not None and ind != previous_anomaly_type):
                    event_counter += 1
                    inside_event = True
                event_counter_list.append(event_counter)
            else:
                event_counter_list.append(0)  # No event, reset to 0
                inside_event = False
            previous_anomaly_type = ind

        self.dataframe['_AnomalyEventNumber'] = event_counter_list


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
        if row['_FieldNoteFlag'] == 0:
            # This data wasn't taken during a field visit
            if row['_ChangeTrends'] == 0 and AnomalyExtractor.is_valid_numeric(row['_ManualChangeAmt']):
                # This data 
                return 'CS'
            elif AnomalyExtractor.is_valid_numeric(row['_ChangeTrends']) and AnomalyExtractor.is_valid_numeric(row['_ManualChangeAmt']):
                return 'LDC'
        return None

    @staticmethod
    def assign_anomaly_type(row, variable_of_interest):
        if variable_of_interest == 'WaterTemp_EXO':
            # Simplified logic for 'WaterTemp_EXO' that ignores calibration events
            if pd.isna(row.get(f'{variable_of_interest}', np.nan)) or row.get(f'{variable_of_interest}', np.nan) == -9999:
                return 1
            elif pd.isna(row.get(f'{variable_of_interest}_QC1', np.nan)) or row.get(f'{variable_of_interest}_QC1', np.nan) == -9999:
                return 3
            elif row.get('_ManualChangeAmt', np.nan) == 0:
                return 0
            else:
                return 2  # Default value
        else:
            # Full logic for other variables
            if row['_FieldNoteFlag'] == 2:
                return 4
            elif row['_CorrectionTypeCal'] in ['CS', 'LDC']:
                return 5
            elif pd.isna(row.get(f'{variable_of_interest}', np.nan)) or row.get(f'{variable_of_interest}', np.nan) == -9999:
                return 1
            elif pd.isna(row.get(f'{variable_of_interest}_QC1', np.nan)) or row.get(f'{variable_of_interest}_QC1', np.nan) == -9999:
                return 3
            elif row.get('_ManualChangeAmt', np.nan) == 0:
                return 0
            else:
                return 2  # Default value

        
