import sys
from pathlib import Path

import yaml
# Add my folder and my parent's folder to Python's import path
my_dir = Path(__file__).resolve().parent
sys.path.append(str(my_dir))
sys.path.append(str(my_dir.parent))
import dataManager as dM
import directoryManager as dirM
import anomalyExtractor as anEx
import anomalyClassifier as anCl

with open(my_dir / "config.yaml", "r") as f:
    config = yaml.safe_load(f)

input_folder = Path(config['input_folder'])
output_folder = Path(config['output_folder'])
raw_aquatic_dataset = Path(config['raw_aquatic_dataset'])
raw_climate_dataset = Path(config['raw_climate_dataset'])
manually_corrected_dataset = Path(config['manually_corrected_dataset'])
field_notes_dataset = Path(config['field_notes_dataset'])
ehsans_results_folder = Path(config['ehsans_results_folder'])


class Configuration:
    def __init__(
            self, variable, site, year, 
            compare_to_file=None, cross_validate_variable="BattVolt", 
            ThrV_1=0.005, ThrV_2=100, ThrV_3=4, PerThr_3=0.5, ThrV_4=10, n=5):
        self.variable = variable
        self.site = site
        self.year = year
        self._set_climate_site()
        self.compare_to_file = compare_to_file
        self.cross_validate_variable = cross_validate_variable
        self.ThrV_1 = ThrV_1
        self.ThrV_2 = ThrV_2
        self.ThrV_3 = ThrV_3
        self.PerThr_3 = PerThr_3
        self.ThrV_4 = ThrV_4
        self.n = n
        self.output = None

    def _set_climate_site(self):
        self.climate_site = "LR_TG_C" if self.site == "LR_TG_BA" else "LR_GC_C"

    def get_compare_to_file(self):
        if self.compare_to_file is not None:
            return self.compare_to_file
        else:
            return (ehsans_results_folder / f"{self.variable}_{self.site}_{self.year}" / "File_1. Final labeling.csv")

    def get_output_file(self):
        if self.output is not None:
            return self.output
        else:
            return (output_folder / f"{self.variable}_{self.site}_{self.year}.csv")

    def __str__(self):
        return f"Configuration(\n"\
            f"  variable={self.variable}, site={self.site}, climate_site={self.climate_site}, year={self.year}\n"\
            f"  Raw: {raw_aquatic_dataset / f'RawAquatic_{self.site}_{self.year}.csv'}\n"\
            f"  QC: {manually_corrected_dataset / f'QC_data_{self.variable}_{self.site}_{self.year}.csv'}\n"\
            f"  FN: {field_notes_dataset / f'FieldNotes_{self.variable}_{self.site}_{self.year}.csv'}\n"\
            f"  Output: {self.get_output_file()}\n"\
            f"  Compare To: {self.get_compare_to_file()}\n"\
            f"  Cross Validate Variable: {self.cross_validate_variable}\n"\
            f")"


class SingleProcessor:
    def __init__(self, config: Configuration, verbose: bool = False):
        self.config = config
        # self.variable_of_interest = config.variable
        # self.site = config.site
        # self.climate_site = config.climate_site
        # self.year = config.year
        # self.cross_validate_variable = config.cross_validate_variable
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
            'Variable': self.config.variable,
            'Site': self.config.site,
            'ClimateSite': self.config.climate_site,
            'Year': self.config.year,
            'crossValidateVariable': self.config.cross_validate_variable,
            'ThrV_1': self.config.ThrV_1,
            'ThrV_2': self.config.ThrV_2,
            'ThrV_3': self.config.ThrV_3,
            'PerThr_3': self.config.PerThr_3,
            'ThrV_4': self.config.ThrV_4,
            'n': self.config.n,
            'CalibrationList': ['Cal', 'CAL', 'Calibration', 'calibration', 'CALIBRATION']
        }
        settings = dM.Settings(settings_dict)

        # Preprocessing #
        dirMan = dirM.DirectoryManager(settings, verbose=self.verbose)
        self.dataMan = dirMan.get_data_manager()

        self.dataMan.validate_as_input(round=10)

    def anomaly_extraction(self, skip=False):
        if self.dataMan == None:
            raise Exception("dataManager is null: Must preprocess data before running anomaly extraction process.")

        # Extracting and Classifying Anomalies
        if not skip:
            extractor = anEx.AnomalyExtractor(self.dataMan, verbose=self.verbose)
            extractor.process()
            self.dataMan.set_main(extractor.dataframe)
            self.dataMan.export_to_csv("_midoutput.csv")
        else: 
            self.dataMan.create_dataframe_from_csv("_midoutput.csv", "MIDOUT", index_col=0, parse_dates=True, low_memory=False)
            self.dataMan.set_main_from_name("MIDOUT")


        classifier = anCl.AnomalyClassifier(self.dataMan, verbose=self.verbose)
        classifier.process()

        # self.dataMan.set_main(extractor.dataframe)

    def export_data(self, filename):
        self.dataMan.export_to_csv(filename, pretty=False)


if __name__ == '__main__':
    output_folder = Path("../_test_results")
    config = Configuration('ODO', 'LR_TG_BA', 2023)
    # print(config)
    # exit()

    processor = SingleProcessor(config, verbose=True)
    processor.preprocess()
    processor.anomaly_extraction(skip=bool(int(sys.argv[1])) if len(sys.argv) > 1 else False)
    output_path = output_folder / "ME.csv"
    processor.export_data(output_path)
    config.output = output_path
