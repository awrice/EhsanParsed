import dataManager as dM
import directoryManager as dirM
import pandas as pd

if __name__ == "__main__":
    # dirMan = dirM.DirectoryManager("../my_output_folder", "../input_folder")
    # dataMan = dM.DataManager(dirMan)
    # settings = dM.Settings("../input_folder/settings.yaml")

    # dataMan.create_dataframe("../input_folder/rawAquatic/RawAquatic_LR_MainStreet_BA_2020.csv", "2020-01-01", "2020-12-31")

    df_0 = pd.date_range(start="01-01 00:00:00", end="12-31 23:45:00", freq="15T")
    df_0 = pd.DataFrame(df_0, columns=['LocalDateTime'])

    print(df_0)
