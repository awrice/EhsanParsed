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
    def __init__(self, directoryManager):
        self.directoryManager = directoryManager
        self.rawDataframes = {}

    # Opens a CSV, creates a dataframe from it, and adds it to the rawDataFrames dictionary under rawDataframes[inputCsvFile]
    @staticmethod
    def create_dataframe_from_csv_static(inputCsvFile, **kwargs):
        df = pd.read_csv(inputCsvFile, sep=',', comment='#', na_values=None, **kwargs)
        return df

    def create_dataframe_from_csv(self, inputCsvFile, name=None, **kwargs):
        if name is None: name = inputCsvFile
        self.rawDataframes[name] = DataManager.create_dataframe_from_csv_static(inputCsvFile, **kwargs)
        return self.rawDataframes[name]

    # combines multiple dataframes (an array) into a single dataframe. Add this dataframe to the rawDataframes dictionary under the specified name
    def combine_dataframes(self, dataframeNames, name, axis=1):
        newDf = pd.DataFrame()
        for df in dataframeNames:
            newDf = pd.concat([newDf, self.rawDataframes[df]], axis=axis)
        self.rawDataframes[name] = newDf

    def add_dataframe(self, dataframe, name):
        self.rawDataframes[name] = dataframe


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
                # this is a beginning time
                events.append(pd.Series({
                    "BeginTime": row["Begin: End time"],
                    "SiteCode": row["SiteCode"],
                    "Method": row["Method"],
                    "QCStatus": row["QC_status"]
                }))

            elif row[eventNumberKey][0] == "N":
                # this is an end time
                events[eventNumber-1]["EndTime"] = row["Begin: End time"]
                if events[eventNumber-1]["SiteCode"] != row["SiteCode"] or events[eventNumber-1]["Method"] != row["Method"]:
                    raise Warning("Extracting Event Data: Site code mismatch between beginning and end times.")
        return pd.DataFrame(events)

