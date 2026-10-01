import pandas as pd
import directoryManager
import yaml

# Setting object holds all required settings to run the analysis
class Settings:
    def __init__(self, settingsYaml):
        with open(settingsYaml, 'r') as f:
            self.settings = yaml.load(f, Loader=yaml.FullLoader)

    def __str__(self):
        return "[Settings: " + str(self.settings) + "]"

# This class represents a dataframe containing input data needed for the analysis we are performing. The dataframe will be validated against this object to see if they are ready for analysis
class InputDataframe:
    INDEX_NAME = "LocalDateTime"
    REQUIRED_COLUMNS = {
        "BattVolt", "EXOVolt", "ODO", "Stage", "pH", "SpCond", "WaterTemp_EXO", "TurbMed", "AirTemp_EE08_avg", "ODO_QC1", "QualifierCode"
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
    def set_main(self, datasetName):
        self.main_dataset_name = datasetName

    def get_main(self):
        return self.dataframes[self.main_dataset_name]

    # exports a dataframe to a CSV file (if dataframe name is not given, exports main)
    def export_to_csv(self, filename, name=None):
        if name is None:
            name = self.main_dataset_name
        if name not in self.dataframes:
            raise ValueError("Dataframe not found")
        self.dataframes[name].to_csv(filename)

    # fieldNotes should be a FieldNotes object
    def add_field_notes(self, fieldNotes):
        self.fieldNotes = fieldNotes

    # combines multiple dataframes (an array) into a single dataframe. Add this dataframe to the dataframes dictionary under the specified name
    def combine_dataframes(self, dataframeNames, name, axis=1):
        newDf = pd.DataFrame()
        for df in dataframeNames:
            newDf = pd.concat([newDf, self.dataframes[df]], axis=axis)
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

    # makes sure a dataframe is ready as an input dataframe -- if name=None, just use the main dataset name
    def validate_as_input(self, name=None, removeUnneededColumns=True):
        if name is None: name = self.main_dataset_name
        if name not in self.dataframes:
            raise ValueError(f"Dataframe {name} not found")
        self.dataframes[name] = InputDataframe(self.dataframes[name])
        if removeUnneededColumns:
            self.dataframes[name].remove_unneeded_columns()


class FieldNotes:
    def __init__(self, inputCsvFile):
        self.dataframe = DataManager.create_dataframe_from_csv_static(inputCsvFile)
        self.events = self.extract_events()

    # extracts the start and end times for each event in a field notes dataframe with the following headers:
    #    Event Number, Begin: End time, SiteCode, Method, QC_status
    # returns a dictionary of events with their start and end times, Site codes, method, and QC status (whether or not this event changed the data at all)
    def extract_events(self):
        eventNumberKey = "Event Number"
        events = []
        for _, row in self.dataframe.iterrows():
            eventNumber = int(row[eventNumberKey][1:])

            if row[eventNumberKey][0] == "B":
                # this is a beginning time entry
                events.append(pd.Series({
                    "BeginTime": row["Begin: End time"],
                    "SiteCode": row["SiteCode"],
                    "Method": row["Method"],
                    "QCStatus": row["QC_status"]
                }))
            elif row[eventNumberKey][0] == "N":
                # this is an end time entry
                if eventNumber > len(events):
                    # this means the beginning of our event is in a row AFTER the end of our event -- likely is just a single minute field note, so we'll just ignore it.
                    continue

                events[eventNumber-1]["EndTime"] = row["Begin: End time"]
                if events[eventNumber-1]["SiteCode"] != row["SiteCode"] or events[eventNumber-1]["Method"] != row["Method"]:
                    print(f"\tWARNING: [Event {eventNumber}] Site code/Method mismatch between beginning and end times. Keeping beginning time.")
                    # raise Warning("Extracting Event Data: Site code mismatch between beginning and end times. Going with the beginning time.")
        
        ret = pd.DataFrame(events)
        ret.rename(columns={'Begin: End time': 'LocalDateTime'}, inplace=True)
        # ret.set_index('LocalDateTime', inplace=True)
        return ret


