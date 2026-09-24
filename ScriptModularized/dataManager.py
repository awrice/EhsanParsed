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
    def create_dataframe_from_csv(self, inputCsvFile, name=None):
        if name is None: name = inputCsvFile
        self.rawDataframes[name] = pd.read_csv(
            inputCsvFile, sep=',', comment='#', parse_dates=['LocalDateTime'], index_col='LocalDateTime', na_values='-9999')

        return True

    

