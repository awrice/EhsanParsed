import dataManager as dM
import directoryManager as dirM
import pandas as pd

if __name__ == "__main__":
    dirMan = dirM.DirectoryManager("../my_output_folder", "../input_folder")
    dataMan = dM.DataManager(dirMan)
    settings = dM.Settings("../input_folder/settings.yaml")

    dataMan.create_dataframe_from_csv(
        "../input_folder/rawAquatic/RawAquatic_LR_MainStreet_BA_2020.csv", name="rawAquatic", 
        parse_dates=['LocalDateTime'], index_col='LocalDateTime')
    dataMan.create_dataframe_from_csv(
        "../input_folder/rawClimate/DataSetClimate_LR_GC_C_2020.csv", name="rawClimate",
        parse_dates=['LocalDateTime'], index_col='LocalDateTime')
    dataMan.create_dataframe_from_csv(
        "../input_folder/manuallyCorrected/QC_data_TurbMed_LR_MainStreet_BA_2020.csv", name="manuallyCorrected",
        parse_dates=['LocalDateTime'], index_col='LocalDateTime')
    fieldNotes = dM.FieldNotes("../input_folder/fieldNotes/FieldNotes_Stage_LR_MainStreet_BA_2020.csv")
    dataMan.add_dataframe(fieldNotes.events, "fieldNotes")

    print(dataMan.rawDataframes["rawAquatic"])
    print(dataMan.rawDataframes["rawClimate"])
    print(dataMan.rawDataframes["manuallyCorrected"])
    print(dataMan.rawDataframes["fieldNotes"])

    dataMan.combine_dataframes(["rawAquatic", "rawClimate", "manuallyCorrected", "fieldNotes"], name="combinedData", axis=1)
    dataMan.rawDataframes["combinedData"].to_csv("../my_output_folder/combinedData.csv")

