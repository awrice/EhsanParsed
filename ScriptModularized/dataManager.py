import pandas as pd
import directoryManager
import yaml

class Settings:
    def __init__(self, settingsYaml):
        with open(settingsYaml, 'r') as f:
            self.settings = yaml.load(f, Loader=yaml.FullLoader)

    def __str__(self):
        return "[Settings: " + str(self.settings) + "]"


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


