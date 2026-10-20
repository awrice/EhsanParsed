import pandas as pd
import directoryManager
import yaml
from typing import Union

# Setting object holds all required settings to run the analysis
class Settings:
    def __init__(self, settingsDict: dict):
        self.settings = settingsDict

    @staticmethod
    def from_yaml(settingsYaml: str):
        with open(settingsYaml, 'r') as f:
            settings = yaml.load(f, Loader=yaml.FullLoader)
        return Settings(settings)

    def __str__(self):
        return "[Settings: " + str(self.settings) + "]"

    def __getitem__(self, key):
        return self.settings[key]

# This class represents a dataframe containing input data needed for the analysis we are performing. The dataframe will be validated against this object to see if they are ready for analysis
class InputDataframe:
    INDEX_NAME = "LocalDateTime"
    REQUIRED_COLUMNS = {
        "BattVolt", "EXOVolt", "ODO", "Stage", "pH", "SpCond", "WaterTemp_EXO", "TurbMed", "AirTemp_EE08_avg"
    }

    def __init__(self, df: pd.DataFrame):
        self._validate_columns(df)
        self._df = df

    @classmethod
    def _validate_columns(cls, df):
        if df.index.name != cls.INDEX_NAME:
            raise ValueError(f"DataFrame index must be named '{cls.INDEX_NAME}', but was '{df.index.name}'")

        missing = cls.REQUIRED_COLUMNS - set(df.columns)
        if missing: raise ValueError(f"DataFrame is missing required columns: {sorted(missing)}")

    def round_all(self, ndigits=6):
        self._df = self._df.round(ndigits)

    # these methods make the InputDataframe behave like a pandas DataFrame
    def __getattr__(self, name):
        """
        If InputDataFrame doesn't have this attribute,
        get it from the underlying DataFrame.
        """
        return getattr(self._df, name)
    def __getitem__(self, key):
        return self._df[key]
    def __setitem__(self, key, value):
        self._df[key] = value
    def __len__(self):
        return len(self._df)

    @property
    def df(self):
        return self._df

    def replace(self, df: pd.DataFrame):
        self._validate_columns(df)
        self._df = df

    def remove_unneeded_columns(self):
        self._df = self._df.drop(columns=[col for col in self._df.columns if col not in self.REQUIRED_COLUMNS])


class DataManager:
    def __init__(self, directoryManager, settings):
        self.directoryManager = directoryManager
        self.settings = settings
        self.dataframes = {}
        self.fieldNotes = None

    # Opens a CSV, creates a dataframe from it, and adds it to the dataframes dictionary under dataframes[inputCsvFile]
    @staticmethod
    def create_dataframe_from_csv_static(inputCsvFile, **kwargs):
        df = pd.read_csv(inputCsvFile, sep=',', comment='#', na_values=None, **kwargs)
        return df

    def create_dataframe_from_csv(self, inputCsvFile, name=None, **kwargs):
        if name is None: name = inputCsvFile
        self.dataframes[name] = DataManager.create_dataframe_from_csv_static(inputCsvFile, **kwargs)
        return self.dataframes[name]
    
    def add_dataframe(self, dataframe, name):
        self.dataframes[name] = dataframe

    # to remove ambiguity of which dataset is the one we're processing, we'll add this simple field of a "main dataset" which can be set anytime
    def set_main_name(self, datasetName):
        self.main_dataset_name = datasetName

    def get_main(self):
        return self.dataframes[self.main_dataset_name]

    def set_main(self, dataframe):
        self.dataframes[self.main_dataset_name] = dataframe

    def set_main_from_name(self, datasetName):
        if datasetName not in self.dataframes:
            raise ValueError(f"Dataframe {datasetName} not found")
        self.main_dataset_name = datasetName

    # exports a dataframe to a CSV file (if dataframe name is not given, exports main)
    def export_to_csv(self, filename, name=None, pretty=False):
        if name is None:
            name = self.main_dataset_name
        if name not in self.dataframes:
            raise ValueError("Dataframe not found")
        if not pretty: self.dataframes[name].to_csv(filename)
        else: DataManager.export_pretty_to_csv(filename, self.dataframes[name])

    @staticmethod
    def export_pretty_to_csv(filename, df):
        data = df.copy()
        data = data.fillna("").astype(str)
        # Calculate the maximum width for each column
        widths = [max(len(str(data.columns[i])), data.iloc[:, i].astype(str).str.len().max()) for i in range(len(data.columns))]
        with open(filename, "w") as f:
            f.write(" , ".join(str(col).ljust(width) for col, width in zip(data.columns, widths)) + "\n")
            for row in data.itertuples(index=False, name=None):
                f.write(" , ".join(str(value).ljust(width) for value, width in zip(row, widths)) + "\n")

    # fieldNotes should be a FieldNotes object
    def add_field_notes(self, fieldNotes):
        self.fieldNotes = fieldNotes

    # Combines multiple dataframes (an array) into a single dataframe. Add this dataframe to the dataframes dictionary under the specified name. Duplicate index values are not allowed for this operation, so we will keep only the first row.
    def combine_dataframes(self, dataframeNames, name, axis=1):
        dfs = []
        for df_name in dataframeNames:
            df = self.dataframes[df_name]
            # Keep only the first row for each duplicate index
            df = df[~df.index.duplicated(keep='first')]
            dfs.append(df)

        newDf = pd.concat(dfs, axis=axis)
        self.dataframes[name] = newDf

    # Loops through the entire dataframe looking for gaps in the data— rows that are not 15 minute intervals to the next row. Empty rows are added, and the dataframe is updated.
    def regulate_localDateTime_dataframe(self, name, interval=15):
        df = self.dataframes[name]

        missing_times = []
        last_row = None
        for row in df.itertuples():
            if last_row is not None:
                time_diff = row.Index - last_row.Index
                if time_diff > pd.Timedelta(minutes=interval):
                    current_time = last_row.Index + pd.Timedelta(minutes=interval)

                    while current_time < row.Index:
                        missing_times.append(current_time)
                        current_time += pd.Timedelta(minutes=interval)
            last_row = row

        # If there are no gaps, then we're good! just return
        if not missing_times: return

        # Otherwise, create empty rows with the same columns as df
        new_rows = pd.DataFrame(
            index=pd.DatetimeIndex(missing_times, name=df.index.name),
            columns=df.columns
        )

        # Add the new rows and sort the dataframe
        df = pd.concat([df, new_rows])
        df = df.sort_index()
        self.dataframes[name] = df

    # Removes a column from a dataframe
    def remove_column(self, name, column_name):
        if name not in self.dataframes:
            raise ValueError(f"Dataframe {name} not found")
        if column_name not in self.dataframes[name].columns:
            raise ValueError(f"Column {column_name} not found")
        self.dataframes[name].drop(columns=[column_name], inplace=True)

    def categorize_time_interval(self, name=None):
        if name is None: name = self.main_dataset_name
        if name not in self.dataframes:
            raise ValueError(f"Dataframe {name} not found")
        
        self.dataframes[name]['TimeInterval'] = self.dataframes[name].index.map(
            lambda dt: "Standard"
            if dt.minute % 15 == 0 and dt.second == 0 and dt.microsecond == 0
            else "Non-Standard"
        )

    # makes sure a dataframe is ready as an input dataframe -- if name=None, just use the main dataset name
    def validate_as_input(self, name=None, removeUnneededColumns=False, round: Union[bool, int] = False, add_interval=True):
        if name is None: name = self.main_dataset_name
        if name not in self.dataframes:
            raise ValueError(f"Dataframe {name} not found")
        self.dataframes[name] = InputDataframe(self.dataframes[name])
        if removeUnneededColumns:
            self.dataframes[name].remove_unneeded_columns()
        if round != False:
            self.dataframes[name].round_all(round)
        if add_interval:
            self.categorize_time_interval()


class FieldNoteEvent:
    EVENT_NUMBER_KEY = "Event Number"

    def __init__(self, event_number, begin_time, end_time, site_code, method):
        self.event_number = event_number
        self.begin_time = begin_time
        self.end_time = end_time
        self.site_code = site_code
        self.method = method

    def __str__(self):
        return f"FieldNoteEvent({self.event_number}): {self.begin_time} to {self.end_time}"

    def combine_with(self, other):
        if self.event_number != other.event_number:
            raise ValueError("Cannot combine events with different event numbers")
        begin_time = self.begin_time if self.begin_time is not None else other.begin_time
        end_time = self.end_time if self.end_time is not None else other.end_time
        site_code = self.site_code if self.site_code is not None else other.site_code
        method = self.method if self.method is not None else other.method
        return FieldNoteEvent(self.event_number, begin_time, end_time, site_code, method)

    def to_series(self):
        return pd.Series({
            "BeginTime": self.begin_time,
            "EventNumber": self.event_number,
            "SiteCode": self.site_code,
            "Method": self.method,
            "EndTime": self.end_time
            # "QCStatus": self.qc_status
            # This column is in many of the field notes files, but not all of them. So we will just ignore it for now.
        })

    @staticmethod
    def from_series(series):
        if series[FieldNoteEvent.EVENT_NUMBER_KEY][0] == "B":
            return FieldNoteEvent(
                event_number=int(series[FieldNoteEvent.EVENT_NUMBER_KEY][1:]),
                begin_time=series["Begin: End time"],
                end_time=None,
                site_code=series.get("SiteCode", None),
                method=series.get("Method", None)
            )
        else:
            return FieldNoteEvent(
                event_number=int(series[FieldNoteEvent.EVENT_NUMBER_KEY][1:]),
                begin_time=None,
                end_time=series["Begin: End time"],
                site_code=series.get("SiteCode", None),
                method=series.get("Method", None)
            )


class FieldNotes:
    def __init__(self, inputCsvFile):
        self.dataframe = DataManager.create_dataframe_from_csv_static(inputCsvFile)
        self.events = self.extract_events()

    # extracts the start and end times for each event in a field notes dataframe with the following headers:
    #    Event Number, Begin: End time, SiteCode, Method, QC_status
    # returns a dictionary of events with their start and end times, Site codes, method, and QC status (whether or not this event changed the data at all)
    def extract_events(self):
        events = []
        for _, row in self.dataframe.iterrows():
            row_event = FieldNoteEvent.from_series(row)
            # Get any other events in the list that have the same event number and are not the current row
            relevant_indices = [i for i, event in enumerate(events) if event.event_number == row_event.event_number]

            if len(relevant_indices) == 0:
                events.append(row_event)
            else:
                # We've seen the other side of this event already, so we need to update it with the new information
                first_index = relevant_indices[0]
                events[first_index] = events[first_index].combine_with(row_event)                

        ret = pd.DataFrame([event.to_series() for event in events])
        ret.rename(columns={'Begin: End time': 'LocalDateTime'}, inplace=True)
        return ret

    def time_in_any_event(self, timestamp):
        for _, row in self.dataframe.iterrows():
            if 'BeginTime' in row and 'EndTime' in row:
                if row['BeginTime'] <= timestamp <= row['EndTime']:
                    return True
        return False


