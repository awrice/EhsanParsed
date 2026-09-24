
#%%
# 2. Importing Libraries, Loading Initial Settings, and Initialize Directories ###################################################################

## 2.1 Import Required Libraries ==========================================================================================================
import re
import yaml
import os as os
import requests
import warnings
import numpy as np
import pandas as pd
import plotly.io as pio
import matplotlib as mpl
from pathlib import Path
import ipywidgets as widgets
from datetime import datetime
from scipy.stats import zscore
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.graph_objects as go
from urllib.parse import urlparse
from IPython.display import display
from matplotlib.ticker import AutoMinorLocator
from typing import Dict, List, Union, Optional, Any
from matplotlib.dates import DayLocator, DateFormatter
from sklearn.linear_model import LinearRegression
import math
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Input, Output, State, dash_table, callback_context
from dash.exceptions import PreventUpdate

#%% 
## 2.2. Defining Directories ==============================================================================================================
# Get the current working directory and assign it to 'scripts_data_folder'
scripts_data_folder = os.getcwd()
# Split the path to get the main folder path (two levels up from 'T_EXO')
main_folder_path = os.path.abspath(os.path.join(scripts_data_folder, ""))
# Define the folders based on the provided diagram
T_EXO_scripts_folder = os.path.join(main_folder_path, 'Scripts', 'T-EXO')
Raw_aquatic_folder = os.path.join(main_folder_path, 'InputDatasets', 'Raw_data', 'RawAquatic')
Raw_climate_folder = os.path.join(main_folder_path, 'InputDatasets', 'Raw_data', 'RawClimate')
FieldNote_data_folder = os.path.join(main_folder_path, 'InputDatasets', 'FieldNote_data')
Processed_data_folder = os.path.join(main_folder_path, 'InputDatasets', 'QC_data')
Plots_folder = os.path.join(main_folder_path, 'Plots')
Results_folder = os.path.join(main_folder_path, 'Results')

# List of folders to check and create if necessary
folders = [Raw_aquatic_folder,
           Raw_climate_folder,
           Processed_data_folder,
           #T_EXO_scripts_folder,
           FieldNote_data_folder,
           Plots_folder,
           Results_folder]

# Check each folder and create it if it does not exist
for folder in folders:
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"Created folder: {folder}")
    else:
        print(f"Folder already exists: {folder}")

scripts_data_folder = os.getcwd() # Get the current working directory

#%% 
## 2.3. Initial Setting (date range, SiteName, Variable, etc) =============================================================================

# Define file path
file_path = "Initial_Settings.yaml" 

# Load YAML file
with open(file_path, "r") as file:
    settings = yaml.safe_load(file)

# Extract the year
year = settings['year']

# Dynamically build the start and end dates using f-strings
start_date = f"{year}{settings['start_date_template']}"
end_date = f"{year}{settings['end_date_template']}"
#start_date_FieldNoteDataset = f"{year}{settings['start_date_FieldNoteDataset_template']}"
#end_date_FieldNoteDataset = f"{year}{settings['end_date_FieldNoteDataset_template']}"

# Extract Key Parameters from the Settings File
Variable = settings["Variable"]
CrossVariable = settings["CrossVariable"]
site        = settings["site"]
Climate_site = settings["Climate_site"]
year = settings["year"]
start_date = start_date
end_date = end_date
#start_date_FieldNoteDataset = start_date_FieldNoteDataset
#end_date_FieldNoteDataset = end_date_FieldNoteDataset
Time_Step_of_data = settings["Time_Step_of_data"]
FieldNotefile_path = settings["FieldNotefile_path"]
#FieldNotefile_link = settings["FieldNotefile_link"]
ThrV_1 = settings["ThrV_1"]
ThrV_2 = settings["ThrV_2"]
ThrV_3 = settings["ThrV_3"]
PerThr_3 = settings["PerThr_3"]
ThrV_4 = settings["ThrV_4"]
n = settings["n"]
Unit = settings["Unit"]
CalibrationList = settings["CalibrationList"]
RetrieveType = settings["RetrieveType"]

# Print selected settings
print(f"Variable: {Variable}")
print(f"Cross Variable: {CrossVariable}")
print(f"Site: {site}")
print(f"Climate Site: {Climate_site}")
print(f"year: {year}")
print(f"start_date: {start_date}")
print(f"end_date: {end_date}")
#print(f"start_date_FieldNoteDataset: {start_date_FieldNoteDataset}")
#print(f"end_date_FieldNoteDataset: {end_date_FieldNoteDataset}")
print(f"Time_Step_of_data: {Time_Step_of_data}")
print(f"FieldNotefile_path: {FieldNotefile_path}")
#print(f"FieldNotefile_link: {FieldNotefile_link}")
print(f"ThrV_1: {ThrV_1}")
print(f"ThrV_2: {ThrV_2}")
print(f"ThrV_3: {ThrV_3}")
print(f"PerThr_3: {PerThr_3}")
print(f"ThrV_4: {ThrV_4}")
print(f"n: {n}")
print(f"Unit: {Unit}")
print(f"CalibrationList: {CalibrationList}")
print(f"RetrieveType: {RetrieveType}")

#%%
# 2.4. Creating the sub-folder for the datasets in the "results" folder, with this format "Variable_site_year": ===================================================================
os.makedirs(Results_folder, exist_ok=True)
Dataset_Dir = f"{Variable}_{site}_{year}"
folder_path = os.path.join(Results_folder, Dataset_Dir)
os.makedirs(folder_path, exist_ok=True)
Dataset_Dir

#%%
# 2.5. Creating the sub-folder for the plots in the "Plots" folder, with this format "Variable_site_year": ===================================================================
os.makedirs(Plots_folder, exist_ok=True)
Plots_Dir = f"{Variable}_{site}_{year}"
folder_path = os.path.join(Plots_folder, Plots_Dir)
os.makedirs(folder_path, exist_ok=True)
Plots_Dir


#%% 3. Importing datasets
## 3.1. Importing the Aquatic Raw Dataset (RawAquaticDataset) =====================================================================================

os.chdir(Raw_aquatic_folder)
# Read the file into a DataFrame
RawAquaticDataset = pd.read_csv(f'RawAquatic_{site}_{year}.csv', sep=',', comment='#', parse_dates=['LocalDateTime'],
                        index_col='LocalDateTime', na_values='-9999')

# Sort and filter the DataFrame
RawAquaticDataset.sort_index(inplace=True)
RawAquaticDataset = RawAquaticDataset[start_date:end_date]
RawAquaticDataset.head(2)

