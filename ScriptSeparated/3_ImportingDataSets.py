#%% 3. Importing datasets
## 3.1. Importing the Aquatic Raw Dataset (RawAquaticDataset) =====================================================================================
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

os.chdir(Raw_aquatic_folder)
# Read the file into a DataFrame
RawAquaticDataset = pd.read_csv(f'RawAquatic_{site}_{year}.csv', sep=',', comment='#', parse_dates=['LocalDateTime'],
                        index_col='LocalDateTime', na_values='-9999')

# Sort and filter the DataFrame
RawAquaticDataset.sort_index(inplace=True)
RawAquaticDataset = RawAquaticDataset[start_date:end_date]
RawAquaticDataset.head(2)

#%%
## 3.2. Importing the climate Climate Raw dataset (DataSetClimate) ==============================================================================

os.chdir(main_folder_path)
os.chdir(Raw_climate_folder)

# Read the file into a DataFrame
DataSetClimate = pd.read_csv(f'DataSetClimate_{Climate_site}_{year}.csv',sep=',',comment='#',parse_dates=['LocalDateTime'],index_col='LocalDateTime',na_values='-9999')

# Sort and filter the DataFrame
DataSetClimate.sort_index(inplace=True)
DataSetClimate = DataSetClimate[start_date:end_date]

DataSetClimate.head(2)

#%%
## 3.3. Importing the Field Note file (FieldNoteDataset) =========================================================================================

os.chdir(main_folder_path)
os.chdir(FieldNote_data_folder)

# Read the file into a DataFrame
FieldNoteDataset = pd.read_csv(f'FieldNotes_{Variable}_{site}_{year}.csv',sep=',',comment='#',parse_dates=['Begin: End time'],index_col='Begin: End time')

# Sort and filter the DataFrame
FieldNoteDataset.sort_index(inplace=True)
FieldNoteDataset = FieldNoteDataset[start_date:end_date]

FieldNoteDataset.head(20)

#%%
## 3.4. Importing the Aquatic QC Dataset (QCDataset) ======================================================================================

os.chdir(main_folder_path)
os.chdir(Processed_data_folder)
QCDataset = pd.read_csv(f'QC_data_{Variable}_{site}_{year}.csv',sep=',',comment='#',parse_dates=['LocalDateTime'],index_col='LocalDateTime',na_values='-9999')

# Filtering time:
QCDataset.sort_index(inplace=True)
QCDataset = QCDataset[start_date:end_date]

QCDataset.head(2)

