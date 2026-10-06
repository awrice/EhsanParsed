import os
import shutil
import dataManager as dM

class DirectoryManager:
    def __init__(self, settings, replace_folder=True, verbose=True):
        self.verbose = verbose
        if self.verbose: print("\033[92m -- Preprocessing -- \033[0m")
        # Get the current working directory and assign it to 'scripts_data_folder'
        self.settings = settings
        self.input_folder = self.settings.settings['input_folder']
        self.output_folder_name = self.settings.settings['output_folder']

        # if output folder name already exists and replace_folder is True, remove it
        if os.path.exists(self.output_folder_name) and replace_folder:
            shutil.rmtree(self.output_folder_name)
        if os.path.exists(self.output_folder_name) and not replace_folder:
            raise Exception("Output folder already exists!") 

        self.output_folder = os.path.join(self.output_folder_name)
        # create directory
        os.makedirs(self.output_folder)

    def get_data_manager(self):
        if self.verbose: print("Assembling Data...")
        dataMan = dM.DataManager(self, self.settings)

        variable_of_interest = self.settings.settings['Variable']
        site = self.settings.settings['Site']
        climate_site = self.settings.settings['ClimateSite']
        year = self.settings.settings['Year']

        # Extract each dataframe we need
        rawAquaticFile = f"{self.settings.settings['rawAquaticDataset']}/RawAquatic_{site}_{year}.csv"
        dataMan.create_dataframe_from_csv(rawAquaticFile, name="rawAquatic", parse_dates=['LocalDateTime'], index_col='LocalDateTime')
        
        climateFile = f"{self.settings.settings['rawClimateDataset']}/DataSetClimate_{climate_site}_{year}.csv"
        dataMan.create_dataframe_from_csv(climateFile, name="rawClimate", parse_dates=['LocalDateTime'], index_col='LocalDateTime')

        manuallyCorrectedFile = f"{self.settings.settings['manuallyCorrectedDataset']}/QC_data_{variable_of_interest}_{site}_{year}.csv"
        dataMan.create_dataframe_from_csv(manuallyCorrectedFile, name="manuallyCorrected", parse_dates=['LocalDateTime'], index_col='LocalDateTime')

        if self.verbose: print("Extracting Field Notes...")
        fieldNotesFile = f"{self.settings.settings['fieldNotesDataset']}/FieldNotes_{variable_of_interest}_{site}_{year}.csv"
        fieldNotes = dM.FieldNotes(fieldNotesFile)
        dataMan.add_field_notes(fieldNotes.events)

        # Now we'll combine the dataframes into one, and set it as our main dataframe
        if self.verbose: print("Combining Dataframes...")
        dataMan.combine_dataframes(["rawAquatic", "rawClimate", "manuallyCorrected"], name="combinedData", axis=1)
        dataMan.regulate_localDateTime_dataframe("combinedData")
        dataMan.set_main_name("combinedData")

        if self.verbose: print("Done!")
        return dataMan


