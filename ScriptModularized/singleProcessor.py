import sys
from pathlib import Path
# Add my folder and my parent's folder to Python's import path
my_dir = Path(__file__).resolve().parent
sys.path.append(str(my_dir))
sys.path.append(str(my_dir.parent))
import dataManager as dM
import directoryManager as dirM
import anomalyExtractor as anEx


input_folder = "../input_folder"
output_folder = "../Results"
raw_aquatic_dataset = f"{input_folder}/rawAquatic"
raw_climate_dataset = f"{input_folder}/rawClimate"
manually_corrected_dataset = f"{input_folder}/manuallyCorrected"
field_notes_dataset = f"{input_folder}/fieldNotes"

ehsans_results_folder = "/Users/a02523625/Documents/HorsburghRA/EhsanData/Results"


class Configuration:
    def __init__(self, variable, site, climate_site, year, compare_to_file=None):
        self.variable = variable
        self.site = site
        self.climate_site = climate_site
        self.year = year
        self.compare_to_file = compare_to_file
        self.output = None

    def get_compare_to_file(self):
        if self.compare_to_file is not None:
            return self.compare_to_file
        else:
            return f"{ehsans_results_folder}/{self.variable}_{self.site}_{self.year}/File_1. Final labeling.csv"

    def get_output_file(self):
        if self.output is not None:
            return self.output
        else:
            return f"{output_folder}/{self.variable}_{self.site}_{self.year}.csv"

    def __str__(self):
        return f"Configuration(\n"\
            f"  variable={self.variable}, site={self.site}, climate_site={self.climate_site}, year={self.year}\n"\
            f"  Raw: {raw_aquatic_dataset}/RawAquatic_{self.site}_{self.year}.csv\n"\
            f"  QC: {manually_corrected_dataset}/{self.variable}_{self.site}_{self.year}.csv\n"\
            f"  FN: {field_notes_dataset}/{self.variable}_{self.site}_{self.year}.csv\n"\
            f"  Output: {self.get_output_file()}\n"\
            f"  Compare To: {self.get_compare_to_file()}\n"\
            f")"


class SingleProcessor:
    def __init__(self, config: Configuration, verbose: bool = False):
        self.variable_of_interest = config.variable
        self.site = config.site
        self.climate_site = config.climate_site
        self.year = config.year
        self.verbose = verbose
        self.dataMan = None

    def preprocess(self):
        settings_dict = {
            'input_folder': input_folder,
            'output_folder': output_folder,
            'rawAquaticDataset': raw_aquatic_dataset,
            'rawClimateDataset': raw_climate_dataset,
            'manuallyCorrectedDataset': manually_corrected_dataset,
            'fieldNotesDataset': field_notes_dataset,
            'Variable': self.variable_of_interest,
            'Site': self.site,
            'ClimateSite': self.climate_site,
            'Year': self.year,
            'CalibrationList': ['Cal', 'CAL', 'Calibration', 'calibration', 'CALIBRATION']
        }
        settings = dM.Settings(settings_dict)

        # Preprocessing #
        dirMan = dirM.DirectoryManager(settings, verbose=self.verbose)
        self.dataMan = dirMan.get_data_manager()
        self.dataMan.validate_as_input()

    def anomaly_extraction(self):
        if self.dataMan == None:
            raise Exception("dataManager is null: Must preprocess data before extracting anomalies")
        # Extracting Anomalies #
        extractor = anEx.AnomalyExtractor(self.dataMan, verbose=self.verbose)
        extractor.process()
        self.dataMan.set_main(extractor.dataframe)

    def export_data(self, filename):
        self.dataMan.export_to_csv(filename)


if __name__ == '__main__':
    output_folder = "../_test_results"
    config = Configuration('Stage', 'LR_MainStreet_BA', 'LR_GC_C', 2024)

    processor = SingleProcessor(config, verbose=True)
    processor.preprocess()
    processor.anomaly_extraction()
    output_path = f"{output_folder}/ME.csv"
    processor.export_data(output_path)
    config.output = output_path
