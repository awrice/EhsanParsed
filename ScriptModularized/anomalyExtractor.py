from kiwisolver import Variable
import numpy as np
import pandas as pd
import re

class AnomalyExtractor:
    def __init__(self, dataManager, verbose=True):
        self.dataManager = dataManager
        self.dataframe = dataManager.get_main()
        self.variable_of_interest = dataManager.settings.settings["Variable"]
        self.verbose = verbose

    """
    Each Method in this class follows the steps given in Ehsan's paper. The sections listed above each method correspond to the section numbers in the paper where the method is described. The paper can be found here: https://drive.google.com/file/d/1D81HE6KTDQp2VLNVsigTh60mVpd6u5PM/view?usp=sharing.

    Lots of the code below was written by Ehsan Kahrizi, but modularized and vetted by Adam Rice

    I have changed the names of the columns from the original paper (because the original names were confusing). Preceeding underscores have been added to the names to denote these are analysis columns, not data columns. The key is given below:
     - RawQCColumn -> _ManualChangeAmt
     - AnomalyIndex -> _IsAnomaly
     - Ind_1 -> _FieldNoteFlag
     - Cal_Counter -> _Cal_Counter
     - CalStartTime -> _CalStartTime
     - CalEndTime -> _CalEndTime
     - iMinePrei -> _ChangeTrends
     - CorrectionTypeCal -> _CorrectionTypeCal
     - AffectedbyCal_Counter -> _CalibrationGroup
     - AffectedCalStartTime -> _CalibrationStart
     - AffectedCalEndTime -> _CalibrationEnd
     - Ind_2 -> _AnomalyType
     - Event_Counter -> _AnomalyEventNumber
     - AffectedCalStartTime2 -> _AnomalyEventStart
     - AffectedCalEndTime2 -> _AnomalyEventEnd
     - RepeatedEvent -> _RepeatedEvent
     - Spike -> _SpikeDetected
     - AnomalyPattern -> _AnomalyPattern
    """

    """
    Master function processes through the steps in the order they should be done. For more info on each step, look to the comments above each method.
    """
    def process(self):
        if self.verbose: print("\033[92m -- Anomaly Extraction -- \033[0m")
        self.point_by_point_difference()
        self.check_field_notes()
        self.process_calibration_events()
        self.calculate_manual_change_trends()
        self.assign_anomaly_types()
        self.extract_events()
        self.flag_flatlines()
        self.detect_spikes()
        self.assign_anomaly_pattern()
        if self.verbose: print("Done!")


    ### Main Process Functions ###
    """
    Section 3.2.2 - Step 1
    Checks to see if there is a difference between our manually changed (QC'ed) data and the raw value we found -- in other words, was this data point manually changed. Adds "_ManualChangeAmt" column which has how far off these values are from each other, as well as a True/False flag in the "_IsAnomaly" column
    """
    def point_by_point_difference(self):
        if self.verbose: print("Calculating Point-by-Point Differences...")
        qc_col = f'{self.variable_of_interest}_QC1'
        raw_col = f'{self.variable_of_interest}'

        # These columns are titled "RawQCColumn" and "AnomalyIndex" in Ehsan's paper -— I think those names are confusing so I changed them
        self.dataframe['_ManualChangeAmt'] = self.dataframe[qc_col] - self.dataframe[raw_col]
        self.dataframe['_IsAnomaly'] = self.dataframe.apply(lambda row: 0 if row[qc_col] == row[raw_col] else 1, axis=1)

    """
    Section 3.2.3 - Step 2
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
        fieldNotes = self.dataManager.fieldNotes.events
        fieldNotes["BeginTime"] = pd.to_datetime(fieldNotes["BeginTime"], format="mixed")
        fieldNotes["EndTime"] = pd.to_datetime(fieldNotes["EndTime"], format="mixed")

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
    Section 3.2.3 - Step 3
    This function is run to specifically identify calibration events, their numbering, start time, and end time. Since the next function assesses the ranges of the time series that are affected by the calibration events, knowing the calibration event numbers is useful. This function scans the '_FieldNoteFlag' column in self.dataframe to find contiguous calibration windows ('_FieldNoteFlag = 2'), numbers them in order, and annotates their start and end rows, adding new columns called 'Cal_Counter', 'CalStartTime', and 'CalEndTime'. If the variable is water temperature, this function is skipped.

    These columns are never used beyond this point for any analysis. Use of these columns would likely be for ML algorithms or other extraction algorithms we'd maybe use after the data is processed.
    """
    def process_calibration_events(self):
        if self.variable_of_interest == "WaterTemp_EXO": return
        if self.verbose: print("Processing Calibration Events...")

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
    Section 3.2.3 - Step 4
    After calibration events are processed, we must identify ranges of data points that are affected by each calibration. This step detects periods outside of the calibration windows (the time period when the field crew was actually at the station) that are likely influenced by the calibration performed by the field crew. The deviation between raw and QC data ('_ManualChangeAmt') and its time-step-to-time-step change (calculated in a column called '_ChangeTrends') is analyzed. For non-water temperature variables, each timestamp with '_FieldNoteFlag = 0' is labeled as 'CS' for “constant shift” and saved in a new column called '_CorrectionTypeCal' when the deviation is nonzero ('_ManualChangeAmt' ≠ 0) and flat ('_ChangeTrends = 0'). Timestamps are labeled as 'LDC' for “linear drift correction” and saved in the '_CorrectionTypeCal' column whenthe deviation is nonzero and changing ('_ChangeTrends ≠ 0'). Consecutive labeled rows aregrouped into a new column called 'AffectedbyCal' events, each assigned an incrementingID called '_CalibrationGroup', with start/end markers added in new columns in the dataframe called '_CalibrationStart' and '_CalibrationEnd', respectively.
    """
    def calculate_manual_change_trends(self):
        if self.verbose: print("Calculating Manual Change Trends...")
        #########################
        # To copy Ehsan's code, we are going to add rows for each field note and then delete them afterwards
        event_times = pd.to_datetime(self.dataManager.fieldNotes.dataframe['Begin: End time'], format="mixed")
        event_rows = pd.DataFrame(index=event_times)
        event_rows.index.name = 'LocalDateTime'
        self.dataframe = pd.concat([self.dataframe, event_rows])
        self.dataframe = self.dataframe.sort_index()
        #########################

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
    Section 3.2.3 - Step 5
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

        #######################################
        # This section is only necessary if we are injecting field notes into our dataframe
        mask = self.dataframe.index.minute % 15 != 0
        self.dataframe.loc[mask, '_AnomalyType'] = np.nan

        event_mask = self.dataframe['_AnomalyType'].isin([1, 2, 3, 4])
        event_indices = self.dataframe[event_mask].index

        # Iterate over event indices to adjust _AnomalyType for the field note rows before/after events
        for idx in event_indices:
            prev_idx = self.dataframe.index.get_loc(idx) - 1
            next_idx = self.dataframe.index.get_loc(idx) + 1

            # Ensure the previous row exists and has 'Non-standard' TimeInterval
            if prev_idx >= 0 and self.dataframe.iloc[prev_idx].name.minute % 15 != 0:
                self.dataframe.iloc[prev_idx, self.dataframe.columns.get_loc('_AnomalyType')] = self.dataframe.loc[idx, '_AnomalyType']

            # Ensure the next row exists and has 'Non-standard' TimeInterval
            if next_idx < len(self.dataframe) and self.dataframe.iloc[next_idx].name.minute % 15 != 0:
                self.dataframe.iloc[next_idx, self.dataframe.columns.get_loc('_AnomalyType')] = self.dataframe.loc[idx, '_AnomalyType']

    """
    Section 3.2.3 - Step 6 & 7
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

        # Start and End Times for each event
        if self.variable_of_interest == 'WaterTemp_EXO':
            return # we don't find these values with this variable

        self.dataframe['_AnomalyEventStart'] = None
        self.dataframe['_AnomalyEventEnd'] = None

        # Initialize tracking variables
        inside_event = False  # Flag to track ongoing events

        for i in range(len(self.dataframe)):
            if self.dataframe.iloc[i]['_AnomalyType'] == 5:  # Only process _AnomalyType == 5 events -- rows affected by calibration afterward ('CorrectionTypeCal'= either 'CS' or 'LDC')
                if not inside_event:  # If entering a new event
                    inside_event = True
                    self.dataframe.loc[self.dataframe.index[i], '_AnomalyEventStart'] = f'Starting time of Event {self.dataframe.iloc[i]["_AnomalyEventNumber"]}'

                # If this is the last row of the event
                if i == len(self.dataframe) - 1 or self.dataframe.iloc[i + 1]['_AnomalyType'] != 5:
                    self.dataframe.loc[self.dataframe.index[i], '_AnomalyEventEnd'] = f'Ending time of Event {self.dataframe.iloc[i]["_AnomalyEventNumber"]}'
                    inside_event = False  # Exit the event

    """
    Section 3.2.3 - Step 8
    We now identify repeated pattern events where the data points are repeated. This step flags flatline behavior within anomaly events by marking rows where the raw data value repeats. After stabilizing float comparisons with a 4-decimal rounding of the QC0 values, the code looks only at rows inside detected events ('_AnomalyEventNumber' > 0), groups them by '_AnomalyEventNumber', and sets '_RepeatedEvent' = 1 for any data values whose numeric value is duplicated anywhere within that event run (ignoring NaNs). Rows without repetition (or outside events) get 0. The goal is to identify 'stuck' or non varying signals (e.g., logger freezes, sensor hold states, or copy-forward artifacts) so they can be summarized separately, used in start/end refinement, or prioritized for QC actions and downstream modeling.
    """
    def flag_flatlines(self):
        if self.verbose: print("Flagging Flatlines...")
        # Initialize the 'RepeatedEvent' column
        self.dataframe['_RepeatedEvent'] = np.nan

        # optional but recommended: stabilize float equality (keep if your data are floats)
        key = self.dataframe[self.variable_of_interest].round(4)

        mask_pos = self.dataframe['_AnomalyEventNumber'] > 0
        repeats = (
            self.dataframe.loc[mask_pos]
            .groupby('_AnomalyEventNumber')[key.name]
            .transform(lambda s: s.duplicated(keep=False) & s.notna())
        )

        self.dataframe.loc[mask_pos, '_RepeatedEvent'] = repeats.fillna(False).astype(int)

    """
    Section 3.2.3 - Step 9
    Next we identify events where the anomaly is a spike. This step detects isolated spike events (i.e., single-sample anomalies) using a robust local outlier test and saves flags in a new column called '_SpikeDetected'. First, it limits candidates to singleton events ('_AnomalyEventNumber' size = 1) with valid raw values (not NaN/-9999). For each candidate row, it inspects a small temporal neighborhood (±3 samples) and computes a robust z-score (equation below). If MAD is zero, it safely falls back to a std-based z-score (and, if needed, a tiny absolute-difference check). Values exceeding the threshold are flagged with '_SpikeDetected'=1; otherwise '_SpikeDetected'=0. Non-candidates remain NaN. The goal is to separate sudden, one-off outliers from multi-point anomalies, enabling cleaner duration estimates, better pattern labeling, and more targeted QC actions.

    z_score = (x - median) / (1.4826 * MAD)
    (Where; 'x' is the data point, 'median' is the middle value of the dataset, and 'MAD' is median absolute deviation.)
    """
    def detect_spikes(self):
        if self.verbose: print("Detecting Isolated Spike Events...")

        # Build masks: singleton events + valid numeric QC0
        # event size per row
        event_size = self.dataframe.groupby('_AnomalyEventNumber')['_AnomalyEventNumber'].transform('size')

        # singleton event rows (and positive event id; drop this if 0/neg are valid)
        singleton_mask = (event_size == 1) & (self.dataframe['_AnomalyEventNumber'] > 0)

        # make a valid raw value mask (numeric, not NaN, not -9999)
        valid_raw_value = self.dataframe[self.variable_of_interest].notna() & (self.dataframe[self.variable_of_interest] != -9999)
        candidates_mask = singleton_mask & valid_raw_value

        self.dataframe['_SpikeDetected'] = np.nan
        # Default everything remains NaN (as you set). We'll write 0/1 only for candidates.
        for idx in self.dataframe.index[candidates_mask]:
            flag = AnomalyExtractor.robust_spike_flag(
                series=self.dataframe[self.variable_of_interest],
                center_idx=idx,
                window=3,          # look 3 rows before and after
                thresh=6.0,        # robust z-score threshold
                min_neighbors=2    # need at least 2 neighbors
            )
            self.dataframe.at[idx, '_SpikeDetected'] = flag

    """
    Section 3.2.3 - Step 10
    The final step (step 10) is to assign the anomaly pattern to each event. This step consolidates multiple anomaly cues into a single, mutually exclusive integer label ('_AnomalyPattern') for every row. It applies a deterministic priority order to resolve overlaps. For variables other than water temperature, calibration corrections take precedence - 'LDC' → 5, 'CS' → 6 - followed by event-code patterns '_AnomalyType'=1 → 1, '_AnomalyType'=3 → 2, then repeated-pattern detectors '_RepeatedEvent'=1 → 3 and '_SpikeDetected'=1 → 4. Anything not captured maps to 7 ('other/none'). For water temperature, calibration classes are intentionally skipped. The final mapping is:

     - '_CorrectionTypeCal' = 'LDC' → 5
     - '_CorrectionTypeCal' = 'CS' → 6
     - '_AnomalyType' = 1 (the raw data value is missing/invalid) → 1
     - '_AnomalyType' = 3 (the manually corrected QC data value is missing/invalid) → 2
     - '_RepeatedEvent' = 1 → 3
     - '_SpikeDetected' = 1 → 4
     - else 7
    
    The goal is to produce a single, consistent target variable that encodes the dominant anomaly pattern per timestamp, simplifying downstream aggregation, visualization, and training/evaluation of ML models.
    """
    def assign_anomaly_pattern(self):
        if self.verbose: print("Assigning Anomaly Patterns...")
        self.dataframe['_AnomalyPattern'] = np.nan

        if self.variable_of_interest == 'WaterTemp_EXO':
            conds = [
                self.dataframe['_AnomalyType'].eq(1),
                self.dataframe['_AnomalyType'].eq(3),
                self.dataframe['_RepeatedEvent'].eq(1),
                self.dataframe['_SpikeDetected'].eq(1)
            ]
            choices = [1, 2, 3, 4]
            self.dataframe['_AnomalyPattern'] = np.select(conds, choices, default=7)

        else:
            # Calibration-related classes come FIRST (highest priority)
            conds = [
                self.dataframe['_CorrectionTypeCal'].eq('LDC'),
                self.dataframe['_CorrectionTypeCal'].eq('CS'),
                self.dataframe['_AnomalyType'].eq(1),
                self.dataframe['_AnomalyType'].eq(3),
                self.dataframe['_RepeatedEvent'].eq(1),
                self.dataframe['_SpikeDetected'].eq(1)
            ]
            choices = [5, 6, 1, 2, 3, 4]
            self.dataframe['_AnomalyPattern'] = np.select(conds, choices, default=7)

        # integer output
        self.dataframe['_AnomalyPattern'] = self.dataframe['_AnomalyPattern'].astype('int64')


    ### Helper Functions ###
    """
    Checks if x is a valid numeric value (not 0, not NaN, and not -9999).
    """
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

    """
    Classifies a row into 'CS' or 'LDC'.
    """
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

    """
    series: the full column (pd.Series) to compute neighbors from (aligned with df index)
    center_idx: the index label (not position) of the candidate row
    window: number of rows to look backward/forward (by position)
    thresh: threshold for robust z-score (|x - median| / (1.4826*MAD))
    min_neighbors: require at least this many neighbors to attempt detection
    """
    @staticmethod
    def robust_spike_flag(series, center_idx, window=3, thresh=6.0, min_neighbors=2):
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


