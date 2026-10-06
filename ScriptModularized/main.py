import dataManager as dM
import directoryManager as dirM
import anomalyExtractor as anEx
import pandas as pd
import sys

settings = dM.Settings("../input_folder/settings.yaml")

def preprocess() -> dM.DataManager:
    # Preprocessing #
    dirMan = dirM.DirectoryManager(settings)
    dataMan = dirMan.get_data_manager()
    dataMan.validate_as_input()
    return dataMan

def anomaly_extraction(dataMan):
    # Extracting Anomalies #

    extractor = anEx.AnomalyExtractor(dataMan, verbose=True)
    extractor.point_by_point_difference()
    extractor.check_field_notes()
    extractor.process_calibration_events()
    extractor.calculate_manual_change_trends()
    extractor.assign_anomaly_types()
    extractor.extract_events()

    
if __name__ == "__main__":
    dataMan = preprocess()
    anomaly_extraction(dataMan)
    dataMan.export_to_csv(f'/Users/a02523625/Documents/HorsburghRA/EhsanParsed/_test_results/{sys.argv[1]}')




def test_regulate_localDateTime_dataframe():
    df = pd.DataFrame({
        'LocalDateTime': [
            pd.Timestamp('2020-01-01 00:00:00'), pd.Timestamp('2020-01-01 00:15:00'), pd.Timestamp('2020-01-01 00:30:00'),
            pd.Timestamp('2020-01-01 00:45:00'), pd.Timestamp('2020-01-01 01:00:00'), pd.Timestamp('2020-01-01 01:15:00'),
            pd.Timestamp('2020-01-01 01:30:00'), pd.Timestamp('2020-01-01 01:45:00'), pd.Timestamp('2020-01-01 02:00:00'),
            pd.Timestamp('2020-01-01 02:15:00'), pd.Timestamp('2020-01-01 02:30:00'), pd.Timestamp('2020-01-01 02:45:00')
        ], 'TurbMed': [
            10, 20, 30, 
            40, 50, 60, 
            70, 80, 90, 
            100, 110, 120
        ], 'TurbMed_QC1': [
            10, 20, 30, 
            40, 50, 60, 
            70, 80, 94, 
            100, 110.001, 120]})
    df = df.set_index('LocalDateTime')

    print(df)

    print(dataMan.regulate_localDateTime_dataframe(df))
