# EhsanParsed

This repository takes Ehsan's code and modularizies it so it's easier to understand and run in multiple environments.

## Required Input Directory/File Format

An input folder, specified in the config.yaml file under the name "input_folder", should have 4 subfolders in it. Each input file's name should be formatted as shown below:
```
input_folder
  ├─fieldNotes
  │  └─ FieldNotes_[variable of interest]_[site]_[year].csv
  ├─manuallyCorrected
  │  └─ QC_data_[variable of interest]_[site]_[year].csv
  ├─rawAquatic
  │  └─ RawAquatic_[site]_[year].csv
  └─rawClimate
     └─ DataSetClimate_[climate site]_[year].csv
```

So if I were running analysis on ODO from LR_WaterLab_AA from the year 2021, and we'd like to use the LR_GC_C climate site, we'd look for the files shown below. If they are not labeled correctly, the process won't work.
```
input_folder
  ├─fieldNotes
  │  └─ FieldNotes_ODO_LR_WaterLab_AA_2021.csv
  ├─manuallyCorrected
  │  └─ QC_data_ODO_LR_WaterLab_AA_2021.csv
  ├─rawAquatic
  │  └─ RawAquatic_LR_WaterLab_AA_2021.csv
  └─rawClimate
     └─ DataSetClimate_LR_GC_C_2021.csv
```

Within each file, there are certain assumptions that we make about the columns and rows in that file. 

### Field Notes:
**Required Columns:**

`Event Number` - Should be of the form "[B or N][Event #]", where B signifies this row is the beginning time of an event, and N signifies this row is the ending time of an event. So if 7 events started before my current row, and I'd like to say a new one is starting, I'd add a row with a "B8" under this column. Then, later in the file, to finish this event, I'd have another row with a "N8". 

`Begin: End time` - This is the timestamp of the event, in the form "yyyy-mm-dd hh:mm:ss", (one example: "2022-05-25 15:40:00")

`SiteCode` - What site this event was taken at. If we're looking in a file called FieldNotes_WaterTemp_EXO_LR_WaterLab_AA_2020.csv, we expect all FieldNotes will have "LR_WaterLab_AA" in this column. 

`Method` - Notes on the site visit. This is used in the anomaly extraction in our AnomalyExtractor.check_field_notes() method. Whether certain keywords are seen in this column affects the _FieldNoteFlag column in our output. 

### QC Data (Manually Corrected):
**Required Columns:**

`LocalDateTime` - Timestamp for this manual correction (we expect these in 15 minute intervals, meaning, we'll only see `yyyy-mm-dd hh:[00 or 15 or 30 or 45]:00` and never `yyyy-mm-dd hh:mm:00` where `mm` % 15 is not 0)

`[variable of interest]_QC1` - Corrected Value for our variable of interest

### Raw Aquatic:
**Required Columns:**

`LocalDateTime` - Just like the QC data, we expect these in 15 minute intervals, meaning, we'll only see `yyyy-mm-dd hh:[00 or 15 or 30 or 45]:00` and never `yyyy-mm-dd hh:mm:00` where `mm` % 15 is not 0

Then we have a series of measurements taken on that timestamp, as follows:

`BattVolt`, `EXOVolt`, `ODO`, `Stage`, `pH`, `SpCond`, `WaterTemp_EXO`, `TurbMed`

*(Note: Even though we are only testing a single variable, we use many of the variables to classify the anomalies we find, so we put ALL this data into the dataframe)*

### Climate Data
**Required Columns:**

`LocalDateTime` - Same 15 minute rule goes for this column. We expect these in 15 minute intervals, meaning, we'll only see `yyyy-mm-dd hh:[00 or 15 or 30 or 45]:00` and never `yyyy-mm-dd hh:mm:00` where `mm` % 15 is not 0

`AirTemp_EE08_avg` - Air temperature measurement at this timestamp

## Code Description

### `singleProcessor.py`
#### Main Components

- **Configuration**: Stores the processing parameters, determines the corresponding climate monitoring site, and manages the paths for comparison and output files.

- **SingleProcessor**: Coordinates preprocessing, anomaly extraction, classification, and data export.

- **config.yaml**: Defines the dataset locations and directory paths used by the processing pipeline.

#### Responsibilities

- **Configuration Management**: Loads file paths from config.yaml and defines processing parameters for the selected variable, site, and year.

- **Data Preprocessing**: Initializes the data management pipeline, retrieves the relevant raw and supporting datasets, and validates the input data.

- **Anomaly Extraction**: Identifies potential anomalies in the preprocessed data using AnomalyExtractor.

- **Anomaly Classification**: Processes the extracted anomalies using AnomalyClassifier to assign classifications based on the configured rules and thresholds.

- **Intermediate Data Storage**: Optionally saves intermediate results to _midoutput.csv, allowing the extraction step to be skipped and processing to resume from previously saved results.

- **Output Export**: Exports the final processed dataset to a CSV file.

### `directoryManager.py`

The DirectoryManager class manages the initial data preprocessing workflow by loading, organizing, and combining the datasets required for analysis. Using the provided configuration settings, it identifies the relevant input files based on the variable of interest, site, climate site, and year.

#### Responsibilities
- **Load raw aquatic data**: Reads the aquatic dataset for the specified site and year, using LocalDateTime as the datetime index.
- **Load raw climate data**: Reads the climate dataset for the specified climate site and year. If present, the BattVolt column is removed.
- **Load manually corrected data**: Imports the quality-controlled dataset for the specified variable, site, and year.
- **Extract field notes**: Loads the corresponding field notes and adds them to the data manager.
- **Combine datasets**: Merges the raw aquatic, raw climate, and manually corrected dataframes along their datetime-indexed columns.
- **Standardize the datetime index**: Regulates the LocalDateTime index of the combined dataset and designates it as the main dataframe.

The `get_data_manager()` method coordinates these operations and returns the populated DataManager object, which contains the combined dataset and associated field notes for subsequent processing and analysis.

The class also supports optional console output through the verbose parameter to indicate preprocessing progress.

### `dataManager.py`

This module provides a set of Python classes for managing, validating, and preparing time-series environmental monitoring data for analysis. It handles CSV data ingestion, DataFrame management, timestamp interval regulation, input validation, and field note processing.

The module is designed to work with environmental sensor datasets and field note datasets that fit the input format outlined above.

The primary goal is to provide a consistent and reliable structure for organizing raw data and preparing it for downstream analysis.

#### Responsibilities
- **Configuration management:** Load analysis settings from YAML files.
- **Data ingestion:** Read CSV files into pandas DataFrames.
- **DataFrame management:** Store and manage multiple datasets, designate a primary dataset, and combine datasets.
- **Timestamp regulation:** Identify missing timestamps and insert empty rows to maintain a consistent sampling interval.
- **Data validation:** Verify that datasets contain the required index and environmental measurement columns.
- **Data preparation:** Round numerical values, remove unnecessary columns, and categorize timestamps as standard or non-standard intervals.
- **CSV export:** Export datasets to CSV files, with an optional human-readable, column-aligned format.
- **Field notes processing:** Extract and combine event information from field notes, including event numbers, start and end times, site codes, and methods.

**Key methods:**

| Method | Description |
|---|---|
| `create_dataframe_from_csv()` | Imports a CSV file and stores the resulting DataFrame. |
| `add_dataframe()` | Adds an existing DataFrame to the manager. |
| `set_main_name()` | Designates the primary dataset by name. |
| `get_main()` | Returns the primary dataset. |
| `set_main_from_name()` | Sets the primary dataset after verifying that it exists. |
| `combine_dataframes()` | Combines named DataFrames into a new dataset. |
| `regulate_localDateTime_dataframe()` | Inserts empty rows for missing timestamps at the specified interval. |
| `categorize_time_interval()` | Adds a `TimeInterval` column to identify standard and non-standard timestamps. |
| `validate_as_input()` | Validates and prepares a dataset for analysis. |
| `export_to_csv()` | Exports a managed dataset to a CSV file. |
| `remove_column()` | Removes a specified column from a dataset. |
| `add_field_notes()` | Associates a `FieldNotes` object with the manager. |

### `anomalyExtractor.py`

This module goes through the steps outlined in Ehsan's paper, section 3.2.3. These steps are complex, and for more detail on each individual process, see the comments above the methods themselves or the Methods Section of Ehsan's paper (lots of the comments above each method come directly from the Methods section of his paper). In very broad strokes, this class is really only meant to have `.process()` called. That function goes through each of the steps sequencially, in the order they should be called (also listed here).

1. `point_by_point_difference()`
2. `check_field_notes()`
3. `process_calibration_events()`
4. `calculate_manual_change_trends()`
5. `assign_anomaly_types()`
6. `extract_events()`
7. `event_start_end_times()`
8. `flag_flatlines()`
9. `detect_spikes()`
10. `assign_anomaly_pattern()`

### `anomalyClassiier.py`
This module is outlined in Ehsan's paper, section 3.2.4. Again, more detail can be found in the paper or in the comments above each method. The main function of this class is also called `.process()`, where each of the following methods are called. All other methods in the class are separated simply for simplification purposes. They are not meant to be called one by one. 

1. `identifyEventTypes()`
2. `check_cross_variable()`
3. `check_ice()`
4. `delta_start_end()`
5. `check_spCond()`
6. `compare_temps()`
7. `compare_ave_stage()`
8. `ind_5_composite()`
9. `maintenance_issues()`
10. `sensor_and_logger_malfunctioning()`
11. `power_issues()`
12. `reading_during_calibration()`
13. `post_calibration_CS()`
14. `post_calibration_LDC()`
15. `final_labeling()`
