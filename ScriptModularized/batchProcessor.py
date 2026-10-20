import sys
from pathlib import Path
# Add my folder and my parent's folder to Python's import path
my_dir = Path(__file__).resolve().parent
sys.path.append(str(my_dir))
sys.path.append(str(my_dir.parent))
from testing.compareResults import CompareCsvDataframes
from singleProcessor import Configuration, SingleProcessor


input_folder = "../input_folder"
output_folder = "../Results"
raw_aquatic_dataset = f"{input_folder}/rawAquatic"
raw_climate_dataset = f"{input_folder}/rawClimate"
manually_corrected_dataset = f"{input_folder}/manuallyCorrected"
field_notes_dataset = f"{input_folder}/fieldNotes"

ehsans_results_folder = "/Users/a02523625/Documents/HorsburghRA/EhsanData/Results/"


class BatchProcessor:
    def __init__(self, configs, output_folder, verbose_level=0):
        self.configs = configs
        self.output_folder = output_folder
        self.verbose_level = verbose_level

    def run(self, compare_while_running=False, run_all=True):
        if self.verbose_level > 0: print(f"\033[92m -- Processing {len(self.configs)} Configuration(s) -- \033[0m")
        count = 1
        for config in self.configs:
            if self.verbose_level > 0: print(f"{count}/{len(self.configs)} : {config.variable} / {config.site} / {config.year}", end="")

            config.output = config.get_output_file()

            if not run_all and self.check_if_already_ran(config):
                if self.verbose_level > 0: print(f" \033[92m (Processed) \033[0m", end="")
            else:
                try:
                    processor = SingleProcessor(config)
                    processor.preprocess()
                    processor.anomaly_extraction()
                    processor.export_data(config.output)
                except Exception as e:
                    # print(f"\033[91m COULDN'T PROCESS - ERRNO: {type(e).__name__} \033[0m", end="")
                    raise e

            if compare_while_running:
                if self.verbose_level > 1: print()
                try:
                    compare = CompareCsvDataframes(config.get_compare_to_file(), config.output, verbose=self.verbose_level > 1)
                    similar = compare.compare()
                    if self.verbose_level > 0:
                        if similar: print(f"\033[92m ✓ \033[0m", end="")
                        else: print(f"\033[91m ✗ \033[0m", end="")
                except Exception as e:
                    print(f"\033[91m COULDN'T COMPARE - ERRNO: {type(e).__name__} \033[0m", end="")

            count += 1
            if self.verbose_level > 0: print()

    def check_if_already_ran(self, config):
        output_path = f"{self.output_folder}/{config.variable}_{config.site}_{config.year}.csv"
        return Path(output_path).exists()

    def compare_all(self):
        for config in self.configs:
            compare = CompareCsvDataframes(config.get_compare_to_file(), config.output, verbose=self.verbose_level > 1)
            compare.compare()



def get_all_configs(variables=None, sites=None, years=None):
    configs = []
    variables = variables if variables is not None else ['Stage', 'pH', 'SpCond', 'ODO', 'WaterTemp_EXO']
    sites = sites if sites is not None else ['LR_TG_BA', 'LR_WaterLab_AA', 'LR_MainStreet_BA', 'BSF_CONF_BA', 'LR_Mendon_AA']
    years = years if years is not None else [2020, 2021, 2022, 2023, 2024]
    for var in variables:
        for site in sites:
            for year in years:
                configs.append(Configuration(var, site, year))
    return configs


if __name__ == '__main__':

    configs = get_all_configs(
        # variables=['WaterTemp_EXO'],
        # sites=None,
        # years=None,
    )
    
    verbose_level = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    batch_processor = BatchProcessor(configs, output_folder, verbose_level)
    
    try:
        run_all = sys.argv[2].lower() == "true" if len(sys.argv) > 2 else False
        batch_processor.run(compare_while_running=True, run_all=run_all)
    except KeyboardInterrupt:
        print("\nExitting early...")
        sys.exit(0)
