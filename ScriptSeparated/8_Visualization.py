
#%%
# 8. Final Dataframe and Visualization ###########################################################################################################

## 8.1. Main file (New dataframe to drop rows that the time-points is out of Standard interval time): =====================================

# Convert 'Event Number' column to string
df_all_Ind1_Ind2['Event_Counter'] = df_all_Ind1_Ind2['Event_Counter'].astype(str)

# Drop rows where 'TimeInterval' is 'Non-standard'
dropped_Field_Note_rows_df = df_all_Ind1_Ind2[df_all_Ind1_Ind2['TimeInterval'] != 'Non-standard']

# Create a true copy of the DataFrame before filtering
filtered_Main_df = dropped_Field_Note_rows_df[['LocalDateTime', f'{Variable}_QC0', f'{Variable}_QC1', 
                                               #'QualifierCode', 
                                               'Label', 
                                               'class']].copy()

# Adding unites to the header of the columns: 
filtered_Main_df = filtered_Main_df.rename(columns={f'{Variable}_QC0': f'{Variable}_QC0 ({Unit})',
                                                    f'{Variable}_QC1': f'{Variable}_QC1 ({Unit})'})

# Replace values in the 'Label' column
filtered_Main_df['Label'] = filtered_Main_df['Label'].replace(['NaN', 'nan', 'None', None], '')

#%%
# Function to prepend class dictionary to the very top of the DataFrame ===================================================================

comments = [
    "# Class Dictionary of the anomalyies label:",
    "# 1: Label is MNT; Maintenance performed",
    "# 2: Label is CAL; Calibration event",
    "# 3: Label is LDC; Linear drift correction applied",
    "# 4: Label is CS; Constant offset correction applied",
    "# 5: Label is PF; Power failure issues observed",
    "# 6: Label is SLM; Sensor or logger malfunction observed",
    "# 7: Label is LWL; Low water level; water dropped and sensor may be exposed to air",
    "# 8: Label is VIN; Not in other classes; needs visual inspection by experts",
    "# 0: Label not in mapping; Data is normal (not an anomaly)",
]

# Choose your output folder/name
os.makedirs(os.path.join(Results_folder, Dataset_Dir), exist_ok=True)
out_path = os.path.join(Results_folder, Dataset_Dir, "File_25.1_Final_labeling_with_class_dictionary.csv")
out_path = os.path.join(Results_folder, Dataset_Dir, "File_2_Final_labeling_with_class_dictionary.csv")

# 1) write comments, 2) append the CSV table
with open(out_path, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(comments) + "\n")
    filtered_Main_df.to_csv(f, index=False)

print(f"CSV saved with comments at top: {out_path}")


#%% 
# 8.2. File of Events =====================================================================================================================

# Create a copy of the original DataFrame
df_copy = df_all_Ind1_Ind2.copy()

# Reinitialize lists for event details
event_numbers = []
start_times = []
end_times = []
durations = []
filed_note_flags = []
begin_times_filed_note = []
end_times_filed_note = []
labels = []
num_data_points = []
duration_of_event = []
mid_QC0 = []
mean_QC0 = []
mid_QC1 = []
mean_QC1 = []
min_QC0 = []
max_QC0 = []
min_QC1 = []
max_QC1 = []

current_event_number = 0

# Iterate through the DataFrame to extract event data
for i, row in df_copy.iterrows():
    if isinstance(row['StartTimeEvent'], str) and 'Starting time of Event' in row['StartTimeEvent']:
        # Increment event number and capture start time
        current_event_number += 1
        event_start_time = row['LocalDateTime']
        
        # Find the end time of the event
        event_end_idx = None
        for j in range(i + 1, len(df_copy)):
            if isinstance(df_copy.loc[j, 'EndTimeEvent'], str) and 'Ending time of Event' in df_copy.loc[j, 'EndTimeEvent']:
                event_end_time = df_copy.loc[j, 'LocalDateTime']
                event_end_idx = j
                break
        
        if event_end_idx is None:
            continue
        
        # Calculate duration in minutes
        duration = (event_end_time - event_start_time).total_seconds() / 60
        durations.append(duration)
        duration_of_event.append(duration)

        # Extract event range
        event_range = df_copy.loc[i:event_end_idx]
        standard_event_range = event_range[event_range['TimeInterval'] == 'Standard']
        num_data_points.append(len(standard_event_range))
        
        
        # Check for Filed Notes (Ind_1 == 1 or 2)
        filed_notes = standard_event_range.loc[standard_event_range['Ind_1'].isin([1, 2])]

        if not filed_notes.empty and 'LocalDateTime' in filed_notes:
            has_filed_note = "Y"
            filed_note_start = filed_notes['LocalDateTime'].iloc[0] if not filed_notes['LocalDateTime'].isna().all() else None
            filed_note_end = filed_notes['LocalDateTime'].iloc[-1] if not filed_notes['LocalDateTime'].isna().all() else None
        else:
            has_filed_note = "N"
            filed_note_start = None
            filed_note_end = None
        
        # Determine the most frequent label in the event range
        if 'Label' in standard_event_range.columns and not standard_event_range['Label'].dropna().empty:
            label_counts = Counter(standard_event_range['Label'].dropna())
            event_label = label_counts.most_common(1)[0][0]  # Get the most frequent label
        else:
            event_label = None
        labels.append(event_label)

        # Define dynamic column names
        var_qc0 = f'{Variable}_QC0'
        var_qc1 = f'{Variable}_QC1'

        # Compute statistics for {Variable}_QC0
        if var_qc0 in standard_event_range.columns and not standard_event_range[var_qc0].dropna().empty:
            mean_QC0.append(standard_event_range[var_qc0].mean())
            mid_QC0.append(standard_event_range[var_qc0].median())
            min_QC0.append(standard_event_range[var_qc0].min())
            max_QC0.append(standard_event_range[var_qc0].max())
        else:
            mean_QC0.append(None)
            mid_QC0.append(None)
            min_QC0.append(None)
            max_QC0.append(None)

        # Compute statistics for {Variable}_QC1
        if var_qc1 in standard_event_range.columns and not standard_event_range[var_qc1].dropna().empty:
            mean_QC1.append(standard_event_range[var_qc1].mean())
            mid_QC1.append(standard_event_range[var_qc1].median())
            min_QC1.append(standard_event_range[var_qc1].min())
            max_QC1.append(standard_event_range[var_qc1].max())
        else:
            mean_QC1.append(None)
            mid_QC1.append(None)
            min_QC1.append(None)
            max_QC1.append(None)

        # Append event details to the lists
        event_numbers.append(current_event_number)
        start_times.append(event_start_time)
        end_times.append(event_end_time)
        filed_note_flags.append(has_filed_note)
        begin_times_filed_note.append(filed_note_start)
        end_times_filed_note.append(filed_note_end)

# Create the final DataFrame and save it as 'new_table_df'
new_table_df = pd.DataFrame({
    'Event No.': event_numbers,
    'Start time of the event': start_times,
    'End time of the event': end_times,
    'Duration (minutes)': durations,
    'Does it have Filed Note?': filed_note_flags,
    'Begin time of Filed Note': begin_times_filed_note,
    'End time of Filed Note': end_times_filed_note,
    'Label': labels,
    'Number of Data Points': num_data_points,
    'Mean QC0': mean_QC0,
    'Mid QC0': mid_QC0,
    'Min QC0': min_QC0,
    'Max QC0': max_QC0,
    'Mean QC1': mean_QC1,
    'Mid QC1': mid_QC1,
    'Min QC1': min_QC1,
    'Max QC1': max_QC1
})

# Display the 'list_df' DataFrame
new_table_df.head()

# Saving:
save_dir = Path(Results_folder) / Dataset_Dir
save_dir.mkdir(parents=True, exist_ok=True)
#output_path = save_dir / "File_26. List of the Events.xlsx"
output_path = save_dir / "File_3. List of the Events.csv"
new_table_df.to_csv(output_path, index=False)
print("File_3. List of the Events to saved to:", output_path)


#%% 
# 8.3. Detailed Information ===============================================================================================================

"""
# Define the data in a dictionary for site name, year, range, time-step, sensor type:
data = {
    'Site_name': site,
    'Year': year,
    'Start_range': start_date,
    'End_range': end_date,
    'Time Step of data' : Time_Step_of_data,
    'Unit' : Unit
    #'Type of Sensor' : Type_of_sensor,
    #'Source of data retrieved' : Source_of_data_retrieved
}
# Convert the dictionary to a DataFrame with rows for each key-value pair
df_site_info = pd.DataFrame(list(data.items()), columns=['Field', 'Value'])

# Combine the 'Field' and 'Value' columns into a single DataFrame with two columns
site_info_combined = pd.DataFrame({
    "Field": df_site_info["Field"].tolist(),
    "Value": df_site_info["Value"].tolist()})

variable_info_combined = pd.DataFrame({
    "Field": Detail_of_QC_data["Field"].tolist(),
    "Value": Detail_of_QC_data["Value"].tolist()})

# Concatenate the site and variable information vertically
df_detailed_info = pd.concat([site_info_combined, variable_info_combined], ignore_index=True)

# Saving:
save_dir = Path(Results_folder) / Dataset_folder
save_dir.mkdir(parents=True, exist_ok=True)
output_path = save_dir / "File_27. Detailed info.xlsx"
df_detailed_info.to_excel(output_path, index=True)
print("Saved to:", output_path)
"""

#%% 
## 8.4 Visualization ======================================================================================================================

# Create a Plotly figure 
fig = go.Figure()
# Plotting the first time series (raw data) without connecting gaps
fig.add_trace(go.Scatter(x=df_all_Ind1_Ind2['LocalDateTime'], y=df_all_Ind1_Ind2[f'{Variable}_QC0'],mode='lines+markers', marker=dict(size=8, symbol='circle'),  name= f'{Variable} Raw Data', line=dict(color='#d62728'),connectgaps=False))                        
# Plotting the second time series (QC)
fig.add_trace(go.Scatter(x=df_all_Ind1_Ind2['LocalDateTime'], y=df_all_Ind1_Ind2[f'{Variable}_QC1'],mode='lines+markers', marker=dict(size=4, symbol='star'),name= f'{Variable} QC Data', line=dict(color='#1f77b4', dash='dot'),connectgaps=True))
# Plotting the RawQCColumn (Raw-QC)
fig.add_trace(go.Scatter(x=df_all_Ind1_Ind2['LocalDateTime'], y=df_all_Ind1_Ind2['RawQCColumn'], mode='lines', name='Difference (Raw - QC)', line=dict(color='black')))

# Adding QualifierCode flags with different markers and colors -----------------------------------------------------
"""
qualifier_codes = ['LI', 'SM', 'PF', 'S', 'ICE', 'MNT', 'PTSCL']
markers = ['circle', 'square', 'diamond', 'triangle-up', 'triangle-down', 'triangle-left', 'triangle-right']
colors = ['#ff7f0e', 'orange', 'green', 'blue', 'purple', 'brown', 'pink']
for code, marker, color in zip(qualifier_codes, markers, colors):
    subset = df_all_Ind1_Ind2[df_all_Ind1_Ind2['QualifierCode'] == code]
    fig.add_trace(go.Scatter(x=subset['LocalDateTime'], y=subset[f'{Variable}_QC1'], mode='markers+text',marker=dict(symbol=marker, size=10, color=color),text=[code] * len(subset),textposition="top center",name=f'Qualifier: {code}'))
"""

# Adding vertical lines for anomaly events -----------------------------------------------------
# Define a dictionary mapping each label to a specific color
label_colors = {'MNT': 'cyan','LWL': 'yellow','SLM': 'orange','CAL': 'cyan','VIN': 'gray','LDC': 'green','CS': 'red','PF': 'blue'}
for idx, row in new_table_df.iterrows():                                                                                    # Iterating through new_table_df and using the 'Start time of the event', 'End time of the event', and 'Label' columns
    if pd.notnull(row['Start time of the event']) and pd.notnull(row['End time of the event']):                             # Ensure that 'Start time of the event' and 'End time of the event' exist
        x_position = row['Start time of the event'] + (row['End time of the event'] - row['Start time of the event']) / 2   # Calculate midpoint of time interval for label placement (horizontal positioning)
        y_position = 1                                                                                                      # You can adjust this value depending on how you want the labels to appear vertically
        color = label_colors.get(row['Label'], 'black')                                                                     # Get the color for the current label 
        fig.add_vrect(x0=row['Start time of the event'], x1=row['End time of the event'], fillcolor=color, opacity=0.1)     # Add vertical rectangle to highlight the time range
        # Add marker and label (using 'Label' column from new_table_df)
        fig.add_trace(go.Scatter(x=[x_position],y=[y_position], mode='markers+text', marker=dict(symbol='x', size=10, color=color),text=[row['Label']], textposition='top center', name=row['Label'], showlegend=False))  # Disable legend for these traces

### Box for showing data point dynamically on hover -------------------------------------------------------------------------------------
hoverinfo='text', 
text=[f"Time: {row.LocalDateTime}<br>Raw Value: {row[f'{Variable}_QC0']}" for _, row in df_all_Ind1_Ind2.iterrows()]               # Modify tooltips for Raw Data
hoverinfo='text', 
text=[f"Time: {row.LocalDateTime}<br>QC Value: {row[f'{Variable}_QC1']}" for _, row in df_all_Ind1_Ind2.iterrows()]                # Modify tooltips for QC Data
hoverinfo='text', 
text=[f"Time: {row.LocalDateTime}<br>Difference: {row['RawQCColumn']}" for _, row in df_all_Ind1_Ind2.iterrows()]                 # Modify tooltips for Difference (Raw - QC)
#hoverinfo='text', 
#text=[f"Qualifier: {code}<br>Time: {row.LocalDateTime}<br>Value: {row[f'{Variable}_QC1']}"for _, row in subset.iterrows()]        # Modify tooltips for Qualifiers
hoverinfo='text', 
text=[f"Event: {row['Label']}<br>Start: {row['Start time of the event']}<br>End: {row['End time of the event']}"]                 # Modify tooltips for Events
fig.update_layout(hoverlabel=dict(font_size=12,font_family="Arial",bgcolor="lightyellow", bordercolor="black",),hovermode='x unified')              # Update layout to adjust hover box size and appearance

# Update layout with titles and labels -----------------------------------------------------
fig.update_layout(
width= 1800,                    # width in pixels
height= 800,                    # height in pixels
# Title Styling
title=dict(text=f'Comparison of {Variable} Data for {site} Station {year}',x=0.5, xanchor='center',font=dict(family="Times New Roman, bold", size=27, color="black")), 
plot_bgcolor='rgba(0,0,0,0)',   # Transparent plot background
paper_bgcolor='rgba(0,0,0,0)',  # Transparent full figure background
# X-Axis Styling
xaxis=dict(title=dict(text='Date',font=dict(family="Times New Roman", size=18, color="black")),
            tickfont=dict(family="Times New Roman", size=16, color="black"),
            showline=True,                                  # Show X-axis border (Bottom)
            linewidth=3,                                    # Border thickness (Bold)
            linecolor='black',                              # Border color (Black)
            mirror=True,                                    # Ensures border on the Top side
            showgrid=True,                                  # Enable X-axis grid (mesh)
            gridcolor='gray',                               # Grid line color
            gridwidth=1.2,                                  # Grid line thickness
            griddash='dot'                                  # Make grid lines dashed
),
# Y-Axis Styling
yaxis=dict(title=dict(text= f'{Variable} ({Unit})',font=dict(family="Times New Roman, bold", size=18, color="black")),
            tickfont=dict(family="Times New Roman", size=16, color="black"),
            showline=True,
            linewidth=3,
            linecolor='black',
            mirror=True,
            showgrid=True,
            gridcolor='gray',
            gridwidth=1.2,
            griddash='dot'),
# Legend Syling
legend=dict(x=0.98, y=0.98,xanchor='right',yanchor='top',bgcolor='rgba(255,255,255,0.8)',bordercolor='black', borderwidth=2, font=dict(family="Times New Roman",size=14,color="black")))

# Show the plot
fig.show()

# Save the figure as an HTML file:
# Define the filename and the full path to save in the 'Plots_folder'
html_filename = f"Plot_1_Univariate plot for {Variable}.html"
html_filepath = os.path.join(Plots_folder, Plots_Dir, html_filename)
# Save the figure as an HTML file in the 'Plots_folder' directory
pio.write_html(fig, file=html_filepath, auto_open=True)
print (f"Plot_1_Univariate plot for {Variable} successfully saved to: {html_filepath}")



#%% 
## 8.5. Zoomed in anomaly events plot ==============================================================================================

mainfile = df_all_Ind1_Ind2
eventfile = new_table_df

# ============ CONFIGURATION PARAMETERS ============
# These parameters can be adjusted to control all aspects of the visualization

EXPORT_PATH = (Path(Plots_folder) / Plots_Dir).resolve()
print(f"[INFO] EXPORT_PATH set to: {EXPORT_PATH}")

# Create a custom path for the variable and year
def get_variable_year_path():
    """Create a custom path based on variable and year."""
    custom_folder = f"Subplots_{Variable}_{year}"
    # Create the full path
    variable_path = os.path.join(EXPORT_PATH, custom_folder)
    # Ensure the directory exists
    if not os.path.exists(variable_path):
        os.makedirs(variable_path)
        print(f"Created directory: {variable_path}")
    # Return with trailing slash to ensure proper path concatenation
    return variable_path + os.sep

# Modified main function to use variable-specific path
def main_with_variable_path():
    # Get the variable-specific path
    var_path = get_variable_year_path()
    print(f"Saving plots to: {var_path}")
    
    # Run the main function with the custom path (no need to add '/' manually)
    main(var_path)

# Font sizes
TITLE_FONT_SIZE = 27       # Main title font size
SUBTITLE_FONT_SIZE = 16    # Subplot titles font size
AXIS_TITLE_FONT_SIZE = 16  # Axis titles font size
TICK_FONT_SIZE = 12        # Axis tick labels font size
LEGEND_FONT_SIZE = 12      # Legend font size

# Font family
FONT_FAMILY = "Arial"
#FONT_FAMILY = "Times New Roman"

# Line widths
AXIS_LINE_WIDTH = 2        # Width of axis lines
GRID_LINE_WIDTH = 1        # Width of grid lines

# Subplot layout
SUBPLOT_WIDTH = 420        # Width of each subplot in pixels
SUBPLOT_HEIGHT = 200       # Height of each subplot in pixels
MAX_COLS = 3               # Maximum number of columns in the grid
                           # Set to None to automatically calculate based on square layout

# Individual plot size
INDIVIDUAL_PLOT_WIDTH = 800   # Width of individual event plots in pixels
INDIVIDUAL_PLOT_HEIGHT = 500   # Height of individual event plots in pixels

# Combined plot size multipliers
COMBINED_PLOT_WIDTH_MULTIPLIER = 1.0   # Multiplier for combined plot width (relative to calculated size)
COMBINED_PLOT_HEIGHT_MULTIPLIER = 1.0  # Multiplier for combined plot height (relative to calculated size)

# Spacing
HORIZONTAL_SPACING = 0.04  # Horizontal spacing between subplots (0-1)
VERTICAL_SPACING = 0.01    # Vertical spacing between subplots (0-1)

# Margins
MARGIN_LEFT = 20           # Left margin in pixels
MARGIN_RIGHT = 20          # Right margin in pixels
MARGIN_TOP = 80            # Top margin in pixels
MARGIN_BOTTOM = 60         # Bottom margin in pixels

# Marker and line configuration
MARKER_SIZE_RAW = 8        # Size of raw data markers
MARKER_SIZE_QC = 6         # Size of QC data markers
MARKER_SIZE_QUALIFIER = 10 # Size of qualifier markers

# Number of data points to include before and after each event
BUFFER_POINTS = 5          # Number of data points to include before and after event

# Legend configuration for individual plots
LEGEND_X_POS = 0.76        # X position (0-1, where 0 is left and 1 is right)
LEGEND_Y_POS = 0.05         # Y position (0-1, where 0 is bottom and 1 is top)
LEGEND_ANCHOR_X = 'left'   # How to anchor the legend horizontally ('left', 'center', 'right')
LEGEND_ANCHOR_Y = 'bottom' # How to anchor the legend vertically ('top', 'middle', 'bottom')
LEGEND_SHOW_BORDER = True  # Whether to show a border around the legend
LEGEND_BG_OPACITY = 0.8    # Opacity of legend background (0-1)
LEGEND_SHOW_QUALIFIERS = False # Whether to show qualifiers in the legend

# Legend configuration for combined plot (separate from individual plots)
COMBINED_LEGEND_X_POS = 0.98        # X position for combined plot legend
COMBINED_LEGEND_Y_POS = 0.02        # Y position for combined plot legend
COMBINED_LEGEND_ANCHOR_X = 'right'  # How to anchor the combined legend horizontally
COMBINED_LEGEND_ANCHOR_Y = 'bottom' # How to anchor the combined legend vertically
COMBINED_LEGEND_SHOW_BORDER = True  # Whether to show a border around the combined legend
COMBINED_LEGEND_BG_OPACITY = 0.9    # Opacity of combined legend background

# Image export configuration
EXPORT_DPI = 400          # DPI for exported images (higher = better quality but larger file size)
EXPORT_FORMAT = 'png'     # Export format (png, jpeg, svg, pdf)
EXPORT_IMAGES = True      # Whether to export images in addition to HTML files

# Define colors for Raw and QC data
#Raw_color = '#1f77b4'
#Raw_color = '#d62728'
Raw_color = 'blue'

#QC_color = '#d62728'
QC_color= 'red'
#QC_color= '#1f77b4'

# Define colors for label types
label_colors = {
    'MNT': 'cyan',
    'LWL': 'yellow',
    'SLM': 'orange',
    'CAL': 'cyan',
    'VIN': 'gray',
    'LDC': 'green',
    'CS': 'red',
    'PF': 'blue'}

# Visualization =====================================
# Function to configure legend position based on settings
def configure_legend(is_combined=False):
    legend_config = {}
    
    # Use different settings based on whether this is for a combined plot or individual plot
    if is_combined:
        # Set custom position coordinates for combined plot
        legend_config.update(
            x=COMBINED_LEGEND_X_POS,
            y=COMBINED_LEGEND_Y_POS,
            xanchor=COMBINED_LEGEND_ANCHOR_X,
            yanchor=COMBINED_LEGEND_ANCHOR_Y)
        
        # Configure background and border for combined plot
        if COMBINED_LEGEND_SHOW_BORDER:
            legend_config.update(
                bgcolor=f'rgba(255,255,255,{COMBINED_LEGEND_BG_OPACITY})',
                bordercolor='black',
                borderwidth=2
            )
        else:
            legend_config.update(
                bgcolor=f'rgba(255,255,255,{COMBINED_LEGEND_BG_OPACITY})',
                borderwidth=0
            )
    else:
        # Set custom position coordinates for individual plots (using original settings)
        legend_config.update(
            x=LEGEND_X_POS,
            y=LEGEND_Y_POS,
            xanchor=LEGEND_ANCHOR_X,
            yanchor=LEGEND_ANCHOR_Y)
        
        # Configure background and border for individual plots
        if LEGEND_SHOW_BORDER:
            legend_config.update(
                bgcolor=f'rgba(255,255,255,{LEGEND_BG_OPACITY})',
                bordercolor='black',
                borderwidth=2
            )
        else:
            legend_config.update(
                bgcolor=f'rgba(255,255,255,{LEGEND_BG_OPACITY})',
                borderwidth=0
            )
    
    # Set font (same for both types)
    legend_config.update(font=dict(family=FONT_FAMILY, size=LEGEND_FONT_SIZE, color="black"))
    return legend_config

# ============  DATA ============
# Function to create a subplot for a specific event
def create_event_subplot(event_row, event_num):
    # Get event details
    start_time = event_row['Start time of the event']
    end_time = event_row['End time of the event']
    event_label = event_row['Label']
    
    # Filter data for the event time range
    event_data = mainfile[(mainfile['LocalDateTime'] >= start_time) & 
                          (mainfile['LocalDateTime'] <= end_time)].copy()
    
    # Get BUFFER_POINTS data points before the event
    before_event = mainfile[mainfile['LocalDateTime'] < start_time].tail(BUFFER_POINTS)
    
    # Get BUFFER_POINTS data points after the event
    after_event = mainfile[mainfile['LocalDateTime'] > end_time].head(BUFFER_POINTS)
    
    # Combine the data sets
    filtered_data = pd.concat([before_event, event_data, after_event]).sort_values('LocalDateTime')
    
    if filtered_data.empty:
        print(f"No data found for event {event_num}: {event_label} from {start_time} to {end_time}")
        return None
    
    # Create figure
    fig = go.Figure()
    
    # Add trace for raw data
    fig.add_trace(go.Scatter(
        x=filtered_data['LocalDateTime'], 
        y=filtered_data[f'{Variable}_QC0'],
        mode='lines+markers', 
        marker=dict(size=MARKER_SIZE_RAW, symbol='circle'),  
        name=f'{Variable} Raw Data', 
        line=dict(color= Raw_color),
        connectgaps=False
    ))
    
    # Add trace for QC data
    fig.add_trace(go.Scatter(
        x=filtered_data['LocalDateTime'], 
        y=filtered_data[f'{Variable}_QC1'],
        mode='lines+markers', 
        marker=dict(size=MARKER_SIZE_QC, symbol='star'),
        name=f'{Variable} QC Data', 
        line=dict(color= QC_color, dash='dot'),
        connectgaps=True
    ))
    
    """
    # Add qualifier markers
    for code, marker, color in zip(qualifier_codes, markers, colors):
        subset = filtered_data[filtered_data['QualifierCode'] == code]
        if not subset.empty:
            fig.add_trace(go.Scatter(
                x=subset['LocalDateTime'], 
                y=subset[f'{Variable}_QC1'], 
                mode='markers+text',
                marker=dict(symbol=marker, size=MARKER_SIZE_QUALIFIER, color=color),
                text=[code] * len(subset),
                textposition="top center",
                name=f'Qualifier: {code}',
                showlegend=LEGEND_SHOW_QUALIFIERS  # Show qualifier in legend based on configuration
            ))
    """
    
    # Add the event highlight
    color = label_colors.get(event_label, 'lightblue')
    fig.add_vrect(
        x0=start_time, 
        x1=end_time, 
        fillcolor=color, 
        opacity=0.2,
        layer="below"
    )
    
    # Add event marker and label
    x_position = start_time + (end_time - start_time) / 2
    fig.add_trace(go.Scatter(
        x=[x_position],
        y=[0], 
        mode='markers+text', 
        marker=dict(symbol='x', size=MARKER_SIZE_QUALIFIER, color=color),
        text=[event_label], 
        textposition='top center', 
        name=event_label, 
        showlegend=False
    ))
    
    # Get legend configuration for individual plots
    legend_config = configure_legend(is_combined=False)
    
    # Update layout with the same styling as original code
    fig.update_layout(
        width=INDIVIDUAL_PLOT_WIDTH,  # Use configurable individual plot width
        height=INDIVIDUAL_PLOT_HEIGHT,  # Use configurable individual plot height
        title=dict(
            text=f'Event {event_num}: {event_label}',
            x=0.5, 
            xanchor='center',
            font=dict(family=FONT_FAMILY, size=TITLE_FONT_SIZE, color="black")
        ),
        plot_bgcolor='rgba(0,0,0,0)',   # Transparent plot background
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent full figure background
        xaxis=dict(
            title=dict(text='Date', font=dict(family=FONT_FAMILY, size=AXIS_TITLE_FONT_SIZE, color="black")),
            tickfont=dict(family=FONT_FAMILY, size=TICK_FONT_SIZE, color="black"),
            showline=True,  # Show X-axis border (Bottom)
            linewidth=AXIS_LINE_WIDTH,  # Border thickness
            linecolor='black',  # Border color (Black)
            mirror=True,  # Ensures border on the Top side
            showgrid=True,  # Enable X-axis grid (mesh)
            gridcolor='gray',  # Grid line color
            gridwidth=GRID_LINE_WIDTH,  # Grid line thickness
            griddash='dot'  # Make grid lines dashed
        ),
        yaxis=dict(
            title=dict(text=f'{Variable} ({Unit})', font=dict(family=FONT_FAMILY, size=AXIS_TITLE_FONT_SIZE, color="black")),
            tickfont=dict(family=FONT_FAMILY, size=TICK_FONT_SIZE, color="black"),
            showline=True,
            linewidth=AXIS_LINE_WIDTH,
            linecolor='black',
            mirror=True,
            showgrid=True,
            gridcolor='gray',
            gridwidth=GRID_LINE_WIDTH,
            griddash='dot'
        ),
        legend=legend_config,
        # Set global font
        font=dict(family=FONT_FAMILY)
    )
    
    return fig


# Optional: Create a combined figure with all events
def create_combined_event_plots():
    # Count valid events
    event_count = len(eventfile)
    # columns
    if MAX_COLS is None:
        cols = math.ceil(math.sqrt(max(event_count, 1)))
    else:
        cols = min(MAX_COLS, max(event_count, 1))

    # rows
    rows = math.ceil(max(event_count, 1) / cols)

    # --- Helpers to pick safe spacings -------------------------------------------
    def _rule_vertical_spacing(n_events: int) -> float:
        """Your requested rule."""
        if n_events >= 80:
            return 0.01
        elif n_events >= 60:
            return 0.015
        elif n_events >= 40:
            return 0.02
        elif n_events >= 20:
            return 0.03
        #elif n_events >= 1:
        #    return 0.04
        else:
            return 0.04

    def _safe_vertical_spacing(n_events: int, cols: int) -> float:
        """Cap by Plotly's limit 1/(rows-1); return 0 if only one row."""
        rows = math.ceil(max(n_events, 1) / max(cols, 1))
        raw = _rule_vertical_spacing(n_events)
        if rows <= 1:
            return 0.0
        max_allowed = 1.0 / (rows - 1)
        # use 95% of the max to avoid equality edge cases
        return max(0.0, min(raw, max_allowed * 0.95))

    def _safe_horizontal_spacing(cols: int, requested: float) -> float:
        """(Optional) also keep horizontal spacing within Plotly's limit."""
        if cols <= 1:
            return 0.0
        max_allowed = 1.0 / (cols - 1)
        return max(0.0, min(requested, max_allowed * 0.95))


    # Create subplot figure with minimal spacing
    fig = make_subplots(
        rows=rows, 
        cols=cols,
        subplot_titles=[f"Event {i+1}: {row['Label']}" for i, row in eventfile.iterrows() 
                       if pd.notnull(row['Start time of the event']) and pd.notnull(row['End time of the event'])],
        vertical_spacing=VERTICAL_SPACING,
        horizontal_spacing=HORIZONTAL_SPACING,
        specs=[[{"type": "xy"} for _ in range(cols)] for _ in range(rows)]
    )
    
    
    # Adjust subplot title font size
    for i in fig['layout']['annotations']:
        i['font'] = dict(size=SUBTITLE_FONT_SIZE, family=FONT_FAMILY)
    
    current_idx = 0
    for idx, event_row in eventfile.iterrows():
        if pd.notnull(event_row['Start time of the event']) and pd.notnull(event_row['End time of the event']):
            # Calculate row and column for this subplot
            row_idx = current_idx // cols + 1
            col_idx = current_idx % cols + 1
            current_idx += 1
            
            # Get event details
            start_time = event_row['Start time of the event']
            end_time = event_row['End time of the event']
            event_label = event_row['Label']
            
            # Filter data for the event time range
            event_data = mainfile[(mainfile['LocalDateTime'] >= start_time) & 
                                  (mainfile['LocalDateTime'] <= end_time)].copy()
            
            # Get BUFFER_POINTS data points before the event
            before_event = mainfile[mainfile['LocalDateTime'] < start_time].tail(BUFFER_POINTS)
            
            # Get BUFFER_POINTS data points after the event
            after_event = mainfile[mainfile['LocalDateTime'] > end_time].head(BUFFER_POINTS)
            
            # Combine the data sets
            filtered_data = pd.concat([before_event, event_data, after_event]).sort_values('LocalDateTime')
            
            if not filtered_data.empty:
                # Add trace for raw data - only show legend in first subplot
                fig.add_trace(
                    go.Scatter(
                        x=filtered_data['LocalDateTime'], 
                        y=filtered_data[f'{Variable}_QC0'],
                        mode='lines+markers', 
                        marker=dict(size=MARKER_SIZE_RAW-2, symbol='circle'),
                        name=f'Raw Data', 
                        line=dict(color=QC_color),
                        showlegend=(row_idx == 1 and col_idx == 1)  # Only show legend for first subplot
                    ),
                    row=row_idx, col=col_idx
                )
                
                # Add trace for QC data - only show legend in first subplot
                fig.add_trace(
                    go.Scatter(
                        x=filtered_data['LocalDateTime'], 
                        y=filtered_data[f'{Variable}_QC1'],
                        mode='lines+markers', 
                        marker=dict(size=MARKER_SIZE_QC-1, symbol='star'),
                        name=f'QC Data', 
                        line=dict(color=Raw_color, dash='dot'),
                        showlegend=(row_idx == 1 and col_idx == 1)  # Only show legend for first subplot
                    ),
                    row=row_idx, col=col_idx
                )
                
                # Add event highlight
                color = label_colors.get(event_label, 'lightblue')
                fig.add_vrect(
                    x0=start_time, 
                    x1=end_time, 
                    fillcolor=color, 
                    opacity=0.2,
                    layer="below",
                    row=row_idx, col=col_idx
                )
                
                
                """
                # Add qualifier markers if present
                # But only show in legend for first subplot if LEGEND_SHOW_QUALIFIERS is True
                for code, marker, color in zip(qualifier_codes, markers, colors):
                    subset = filtered_data[filtered_data['QualifierCode'] == code]
                    if not subset.empty:
                        fig.add_trace(
                            go.Scatter(
                                x=subset['LocalDateTime'], 
                                y=subset[f'{Variable}_QC1'], 
                                mode='markers+text',
                                marker=dict(symbol=marker, size=MARKER_SIZE_QUALIFIER-2, color=color),
                                text=[code] * len(subset),
                                textposition="top center",
                                name=f'Qualifier: {code}',
                                showlegend=(row_idx == 1 and col_idx == 1 and LEGEND_SHOW_QUALIFIERS)
                            ),
                            row=row_idx, col=col_idx
                        )
                """
                
    # Get legend configuration for combined plot
    legend_config = configure_legend(is_combined=True)
    
    # Update layout for the combined figure with styling from original code
    fig.update_layout(
        height=int(SUBPLOT_HEIGHT*rows*COMBINED_PLOT_HEIGHT_MULTIPLIER),
        width=int(SUBPLOT_WIDTH*cols*COMBINED_PLOT_WIDTH_MULTIPLIER),
        title=dict(
            #text = f'Zoomed in on all the detected anomaly events of {Variable} data at {site} Station in {year}',
            text = f'Zoomed in on all the events of {Variable} data at {site} Station in {year}',
            x=0.5, 
            xanchor='center',
            font=dict(family=FONT_FAMILY, size=TITLE_FONT_SIZE, color="black")
        ),
        plot_bgcolor='rgba(0,0,0,0)',   # Transparent plot background
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent full figure background
        showlegend=True,  # Ensure legend is shown
        legend=legend_config,
        # Tight margins to maximize plotting area
        margin=dict(l=MARGIN_LEFT, r=MARGIN_RIGHT, t=MARGIN_TOP, b=MARGIN_BOTTOM, pad=0),
        # Set global font
        font=dict(family=FONT_FAMILY)
    )
    
    # Update axes properties for all subplots with consistent styling
    for i in range(1, rows+1):
        for j in range(1, cols+1):
            # Only show y-axis title for the leftmost subplots (first column)
            if j == 1:
                fig.update_yaxes(
                    title=dict(text=f'{Variable} ({Unit})', font=dict(family=FONT_FAMILY, size=AXIS_TITLE_FONT_SIZE, color="black")),
                    row=i, col=j
                )
            
            # Only show x-axis title for the bottom row
            if i == rows:
                fig.update_xaxes(
                    title=dict(text='Date', font=dict(family=FONT_FAMILY, size=AXIS_TITLE_FONT_SIZE, color="black")),
                    row=i, col=j
                )
            
            # Apply common styling to all axes but use smaller fonts and minimize elements
            fig.update_xaxes(
                showline=True,
                linewidth=AXIS_LINE_WIDTH,
                linecolor='black',
                mirror=True,
                showgrid=True,
                gridcolor='gray',
                gridwidth=GRID_LINE_WIDTH,
                griddash='dot',
                tickfont=dict(family=FONT_FAMILY, size=TICK_FONT_SIZE, color="black"),
                # Reduce number of ticks to save space
                nticks=5,
                row=i, col=j
            )
            
            fig.update_yaxes(
                showline=True,
                linewidth=AXIS_LINE_WIDTH,
                linecolor='black',
                mirror=True,
                showgrid=True,
                gridcolor='gray',
                gridwidth=GRID_LINE_WIDTH,
                griddash='dot',
                tickfont=dict(family=FONT_FAMILY, size=TICK_FONT_SIZE, color="black"),
                # Reduce number of ticks to save space
                nticks=5,
                row=i, col=j
            )
    
    return fig


# Create subplots for each event
def main(output_path=""):
    event_count = len(eventfile)
    print(f"Processing {event_count} events...")

    # Create individual plots for each event
    for idx, event_row in eventfile.iterrows():
        event_num = idx + 1
        # Check if start and end times exist
        if pd.notnull(event_row['Start time of the event']) and pd.notnull(event_row['End time of the event']):
            fig = create_event_subplot(event_row, event_num)
            if fig is not None:
                # Generate base filename without extension
                base_filename = f"Event_{event_num}_{event_row['Label']}_zoom"
                
                # Save as HTML file with output path
                html_filename = f"{output_path}{base_filename}.html"
                pio.write_html(fig, file=html_filename, auto_open=False)
                print(f"Saved {html_filename}")
                
                # Export as image file if enabled
                if EXPORT_IMAGES:
                    img_filename = f"{output_path}{base_filename}.{EXPORT_FORMAT}"
                    fig.write_image(img_filename, scale=EXPORT_DPI/100)  # Scale converts DPI to Plotly's scale factor
                    print(f"Exported image: {img_filename} at {EXPORT_DPI} DPI")

    print("All individual event subplots have been created!")

    # Create and save the combined plot
    combined_fig = create_combined_event_plots()
    
    # Save combined plot as HTML with output path
    combined_html = f"{output_path}All_Events_{site}_{year}_combined.html"
    pio.write_html(combined_fig, file=combined_html, auto_open=True)
    print(f"Combined events plot created as {combined_html}")
    
    # Export combined plot as image if enabled
    if EXPORT_IMAGES:
        combined_img = f"{output_path}All_Events_{site}_{year}_combined.{EXPORT_FORMAT}"
        combined_fig.write_image(combined_img, scale=EXPORT_DPI/100)
        print(f"Exported combined image: {combined_img} at {EXPORT_DPI} DPI")

def main_with_variable_path():
    # Get the variable-specific path
    var_path = get_variable_year_path()
    print(f"Saving plots to: {var_path}")
    main(var_path + '/')

if __name__ == "__main__":
    main_with_variable_path()


#%% 
## 8.6. Multivariate 'Variable' + 'CrossVariable' plot ==============================================================================================


# Create a Plotly figure
fig=go.Figure()
# Adding the second y-axis data (OtherVar_QC0) to the right side of the plot
fig.add_trace(go.Scatter(x=df_all_Ind1_Ind2['LocalDateTime'],y=df_all_Ind1_Ind2[f'{CrossVariable}_QC0'],mode='lines+markers',marker=dict(size=4,symbol='diamond'),name=f'{CrossVariable}_QC0',line=dict(color='#bcbd22'),yaxis='y2',opacity=0.6))
# Plotting the first time series (raw data) without connecting gaps
fig.add_trace(go.Scatter(x=df_all_Ind1_Ind2['LocalDateTime'],y=df_all_Ind1_Ind2[f'{Variable}_QC0'],mode='lines+markers',marker=dict(size=8,symbol='circle'),name=f'{Variable} Raw Data',line=dict(color='#d62728'),connectgaps=False))
# Plotting the second time series (QC)
fig.add_trace(go.Scatter(x=df_all_Ind1_Ind2['LocalDateTime'],y=df_all_Ind1_Ind2[f'{Variable}_QC1'],mode='lines+markers',marker=dict(size=4,symbol='star'),name=f'{Variable} QC Data',line=dict(color='#1f77b4',dash='dot'),connectgaps=True))
# Plotting the RawQCColumn (Raw-QC)
fig.add_trace(go.Scatter(x=df_all_Ind1_Ind2['LocalDateTime'],y=df_all_Ind1_Ind2['RawQCColumn'],mode='lines',name='Difference (Raw - QC)',line=dict(color='black')))
# Update the layout to add the secondary y-axis
fig.update_layout(yaxis2=dict(title=f'{CrossVariable}_QC0',overlaying='y',side='right',showgrid=False,zeroline=True,layer='below traces'))







# Adding QualifierCode flags with different markers and colors -------------------------------------------------------------
"""
qualifier_codes = ['LI', 'SM', 'PF', 'S', 'ICE', 'MNT', 'PTSCL']
markers = ['circle', 'square', 'diamond', 'triangle-up', 'triangle-down', 'triangle-left', 'triangle-right']
colors = ['#ff7f0e', 'orange', 'green', 'blue', 'purple', 'brown', 'pink']
for code, marker, color in zip(qualifier_codes, markers, colors):
    subset = df_all_Ind1_Ind2[df_all_Ind1_Ind2['QualifierCode'] == code]
    fig.add_trace(go.Scatter(x=subset['LocalDateTime'], y=subset[f'{Variable}_QC1'], mode='markers+text',marker=dict(symbol=marker, size=10, color=color),text=[code] * len(subset),textposition="top center",name=f'Qualifier: {code}'))
"""

# Adding vertical lines for events -------------------------------------------------------------------------------------
# Define a dictionary mapping each label to a specific color
label_colors = {'MNT': 'purple','LWL': 'yellow','SLM': 'orange','CAL': 'cyan','VIN': 'gray','LDC': 'green','CS': 'red', 'PF': 'blue'}
# Iterating through new_table_df and using the 'Start time of the event', 'End time of the event', and 'Label' columns
for idx, row in new_table_df.iterrows():
    # Ensure that 'Start time of the event' and 'End time of the event' exist
    if pd.notnull(row['Start time of the event']) and pd.notnull(row['End time of the event']):
        # Calculate midpoint of time interval for label placement (horizontal positioning)
        x_position = row['Start time of the event'] + (row['End time of the event'] - row['Start time of the event']) / 2
        # Use a static y-position, as you are no longer calculating the y-value from RawAquaticDataset
        y_position = 1  # You can adjust this value depending on how you want the labels to appear vertically
        # Get the color for the current label
        color = label_colors.get(row['Label'], 'black')  # Default to black if the label is not in the dictionary
        # Add vertical rectangle to highlight the time range
        fig.add_vrect(x0=row['Start time of the event'], x1=row['End time of the event'], fillcolor=color, opacity=0.1)
        # Add marker and label (using 'Label' column from new_table_df)
        fig.add_trace(go.Scatter(x=[x_position],y=[y_position], mode='markers+text',marker=dict(symbol='x', size=10, color=color), text=[row['Label']], textposition='top center',name=row['Label'],showlegend=False))  # Disable legend for these traces

### Box for showing data point dynamically on hover -------------------------------------------------------------------------------------
# Modify tooltips for Raw Data
hoverinfo='text',
text=[f"Time: {row.LocalDateTime}<br>Raw Value: {row[f'{Variable}_QC0']}"for _, row in df_all_Ind1_Ind2.iterrows()]
# Modify tooltips for QC Data
hoverinfo='text',
text=[f"Time: {row.LocalDateTime}<br>QC Value: {row[f'{Variable}_QC1']}"for _, row in df_all_Ind1_Ind2.iterrows()]
# Modify tooltips for Difference (Raw - QC)
hoverinfo='text',
text=[f"Time: {row.LocalDateTime}<br>Difference: {row['RawQCColumn']}"for _, row in df_all_Ind1_Ind2.iterrows()]
# Modify tooltips for Qualifiers
#hoverinfo='text',
#text=[f"Qualifier: {code}<br>Time: {row.LocalDateTime}<br>Value: {row[f'{Variable}_QC1']}"for _, row in subset.iterrows()]
# Modify tooltips for Events
hoverinfo='text',
text=[f"Event: {row['Label']}<br>Start: {row['Start time of the event']}<br>End: {row['End time of the event']}"]
# Update layout to adjust hover box size and appearance
fig.update_layout(hoverlabel=dict(font_size=12,  font_family="Arial",  bgcolor="lightyellow", bordercolor="black", ), hovermode='x unified')
    
# Update layout with titles and labels -----------------------------------------------------
fig.update_layout(
#Size
width= 1800,  # width in pixels
height= 800,   # height in pixels
# Title Styling
title=dict(text=f'Comparison of {Variable} and {CrossVariable} Data for {site} Station {year}',x=0.5, xanchor='center',font=dict(family="Times New Roman, bold", size=27, color="black")),
plot_bgcolor='rgba(0,0,0,0)',   # Transparent plot background
paper_bgcolor='rgba(0,0,0,0)',  # Transparent full figure background
# X-Axis Styling
xaxis=dict(title=dict(text='Date',font=dict(family="Times New Roman", size=18, color="black")),
            tickfont=dict(family="Times New Roman", size=16, color="black"),
            showline=True,  # Show X-axis border (Bottom)
            linewidth=3,  # Border thickness (Bold)
            linecolor='black',  # Border color (Black)
            mirror=True,  # Ensures border on the Top side
            showgrid=True,  # Enable X-axis grid (mesh)
            gridcolor='gray',  # Grid line color
            gridwidth=1.2,  # Grid line thickness
            griddash='dot'  # Make grid lines dashed
),
# Y-Axis Styling
yaxis=dict(title=dict(text= f'{Variable} ({Unit})',font=dict(family="Times New Roman, bold", size=18, color="black")),
            tickfont=dict(family="Times New Roman", size=16, color="black"),
            showline=True,
            linewidth=3,
            linecolor='black',
            mirror=True,
            showgrid=True,
            gridcolor='gray',
            gridwidth=1.2,
            griddash='dot'),
# Legend Syling
legend=dict(x=0.98, y=0.98,xanchor='right',yanchor='top',bgcolor='rgba(255,255,255,0.8)',bordercolor='black', borderwidth=2, font=dict(family="Times New Roman",size=14,color="black")))
                    
# Show the plot
fig.show()

# Save the figure as an HTML file:
# Define the filename and the full path to save in the 'Plots_folder'
html_filename = f"Plot_2_Multivariate plot for {Variable} and {CrossVariable}_QC0.html"
html_filepath = os.path.join(Plots_folder, Plots_Dir, html_filename)
# Save the figure as an HTML file in the 'Plots_folder' directory
pio.write_html(fig, file=html_filepath, auto_open=True)
print(f"Plot_2_Multivariate plot for {Variable} and {CrossVariable}_QC0 successfully saved to: {html_filepath}")


#%% 
## 8.7. Multivariate 'Variable' + 'WaterTemp_EXO_QC0' + 'DataSetClimate' plot =========================================================================

# Create a Plotly figure
fig = go.Figure()
# Adding the second y-axis data (OtherVar_QC0) to the right side of the plot
fig.add_trace(go.Scatter(x=df_all_Ind1_Ind2['LocalDateTime'], y=df_all_Ind1_Ind2['AirTemp'],mode='lines+markers',marker=dict(size=4, symbol='x'),name='AirTemp',line=dict(color='#7f7f7f', dash='dash'), yaxis='y2',opacity=0.6))
# Adding the second y-axis data (WaterTemp_EXO_QC0) to the right side of the plot
fig.add_trace(go.Scatter(x=df_all_Ind1_Ind2['LocalDateTime'], y=df_all_Ind1_Ind2['WaterTemp_EXO_QC0'],mode='lines+markers',marker=dict(size=4, symbol='diamond'),name= 'WaterTemp_EXO_QC0',line=dict(color='#bcbd22'), yaxis='y2',opacity=0.6))
# Plotting the first time series (raw data) without connecting gaps
fig.add_trace(go.Scatter(x=df_all_Ind1_Ind2['LocalDateTime'], y=df_all_Ind1_Ind2[f'{Variable}_QC0'],mode='lines+markers',  marker=dict(size=8, symbol='circle'),  name= f'{Variable} Raw Data', line=dict(color='#d62728'),connectgaps=False)) 
# Plotting the second time series (QC)
fig.add_trace(go.Scatter(x=df_all_Ind1_Ind2['LocalDateTime'], y=df_all_Ind1_Ind2[f'{Variable}_QC1'],mode='lines+markers', marker=dict(size=4, symbol='star'),name= f'{Variable} QC Data',line=dict(color='#1f77b4', dash='dot'),connectgaps=True))
# Plotting the RawQCColumn (Raw-QC)
fig.add_trace(go.Scatter(x=df_all_Ind1_Ind2['LocalDateTime'], y=df_all_Ind1_Ind2['RawQCColumn'],mode='lines', name='Difference (Raw - QC)', line=dict(color='black')))
# Update the layout to add the secondary y-axis
fig.update_layout(yaxis2=dict(title='Temprature(ºC)', overlaying='y', side='right', automargin=True, showgrid=False, zeroline=True))

# Adding QualifierCode flags with different markers and colors -----------------------------------------------------
"""
qualifier_codes = ['LI', 'SM', 'PF', 'S', 'ICE', 'MNT', 'PTSCL']
markers = ['circle', 'square', 'diamond', 'triangle-up', 'triangle-down', 'triangle-left', 'triangle-right']
colors = ['#ff7f0e', 'orange', 'green', 'blue', 'purple', 'brown', 'pink']
for code, marker, color in zip(qualifier_codes, markers, colors):
    subset = df_all_Ind1_Ind2[df_all_Ind1_Ind2['QualifierCode'] == code]
    fig.add_trace(go.Scatter(x=subset['LocalDateTime'], y=subset[f'{Variable}_QC1'], mode='markers+text',marker=dict(symbol=marker, size=10, color=color),text=[code] * len(subset),textposition="top center",name=f'Qualifier: {code}'))
"""

# Adding vertical lines for events:-------------------------------------------------------
# Define a dictionary mapping each label to a specific color
label_colors = {'MNT': 'purple','LWL': 'yellow','SLM': 'orange','CAL': 'cyan','VIN': 'gray','LDC': 'green','CS': 'red','PF': 'blue'}
# Iterating through new_table_df and using the 'Start time of the event', 'End time of the event', and 'Label' columns
for idx, row in new_table_df.iterrows():
    # Ensure that 'Start time of the event' and 'End time of the event' exist
    if pd.notnull(row['Start time of the event']) and pd.notnull(row['End time of the event']):
        # Calculate midpoint of time interval for label placement (horizontal positioning)
        x_position = row['Start time of the event'] + (row['End time of the event'] - row['Start time of the event']) / 2
        # Use a static y-position, as you are no longer calculating the y-value from RawAquaticDataset
        y_position = 1  # You can adjust this value depending on how you want the labels to appear vertically
        # Get the color for the current label
        color = label_colors.get(row['Label'], 'black')  # Default to black if the label is not in the dictionary
        # Add vertical rectangle to highlight the time range
        fig.add_vrect(x0=row['Start time of the event'], x1=row['End time of the event'], fillcolor=color, opacity=0.1)
        # Add marker and label (using 'Label' column from new_table_df)
        fig.add_trace(go.Scatter(x=[x_position], y=[y_position], mode='markers+text',marker=dict(symbol='x', size=10, color=color), text=[row['Label']], textposition='top center',name=row['Label'],showlegend=False)) 

### Box for showing data point dynamically on hover-------------------------------------------------------------------------------------
# Modify tooltips for Raw Data
hoverinfo='text',
text=[f"Time: {row.LocalDateTime}<br>Raw Value: {row[f'{Variable}_QC0']}"for _, row in df_all_Ind1_Ind2.iterrows()]
# Modify tooltips for QC Data
hoverinfo='text',
text=[f"Time: {row.LocalDateTime}<br>QC Value: {row[f'{Variable}_QC1']}"for _, row in df_all_Ind1_Ind2.iterrows()]
# Modify tooltips for Difference (Raw - QC)
hoverinfo='text',
text=[f"Time: {row.LocalDateTime}<br>Difference: {row['RawQCColumn']}"for _, row in df_all_Ind1_Ind2.iterrows()]
# Modify tooltips for Qualifiers
#hoverinfo='text',
#text=[f"Qualifier: {code}<br>Time: {row.LocalDateTime}<br>Value: {row[f'{Variable}_QC1']}"for _, row in subset.iterrows()]
# Modify tooltips for Events
hoverinfo='text',
text=[f"Event: {row['Label']}<br>Start: {row['Start time of the event']}<br>End: {row['End time of the event']}"]
# Update layout to adjust hover box size and appearance
fig.update_layout(hoverlabel=dict(font_size=12,  font_family="Arial",  bgcolor="lightyellow", bordercolor="black",  ),hovermode='x unified')

# Update layout with titles and labels -----------------------------------------------------
fig.update_layout(
#Size
width= 1800,  # width in pixels
height= 800,   # height in pixels
# Title Styling
title=dict(text=f'Comparison of {Variable}, WaterTemp, and DataSetClimate Data for {site} Station {year}',x=0.5, xanchor='center',font=dict(family="Times New Roman, bold", size=27, color="black")),
plot_bgcolor='rgba(0,0,0,0)',   # Transparent plot background
paper_bgcolor='rgba(0,0,0,0)',  # Transparent full figure background
# X-Axis Styling
xaxis=dict(title=dict(text='Date',font=dict(family="Times New Roman", size=18, color="black")),
            tickfont=dict(family="Times New Roman", size=16, color="black"),
            showline=True,  # Show X-axis border (Bottom)
            linewidth=3,  # Border thickness (Bold)
            linecolor='black',  # Border color (Black)
            mirror=True,  # Ensures border on the Top side
            showgrid=True,  # Enable X-axis grid (mesh)
            gridcolor='gray',  # Grid line color
            #automargin=True,
            gridwidth=1.2,  # Grid line thickness
            griddash='dot'  # Make grid lines dashed
),
# Y-Axis Styling
yaxis=dict(title=dict(text= f'{Variable} ({Unit})',font=dict(family="Times New Roman, bold", size=18, color="black")),
            tickfont=dict(family="Times New Roman", size=16, color="black"),
            showline=True,
            linewidth=3,
            linecolor='black',
            mirror=True,
            showgrid=True,
            #automargin=True,
            gridcolor='gray',
            gridwidth=1.2,
            griddash='dot'), 
            #margin=dict(l=100, r=120, t=50, b=50),
# Legend Syling
legend=dict(x=0.98, y=0.98,xanchor='right',yanchor='top',bgcolor='rgba(255,255,255,0.8)',bordercolor='black', borderwidth=2, font=dict(family="Times New Roman",size=14,color="black")))
    
# Show the plot
fig.show()

# Save the figure as an HTML file:
# Define the filename and the full path to save in the 'Plots_folder'
html_filename = f"Plot_3_Multivariate plot for {Variable}, WaterTemp, and DataSetClimate.html"
html_filepath = os.path.join(Plots_folder, Plots_Dir, html_filename)
# Save the figure as an HTML file in the 'Plots_folder' directory
pio.write_html(fig, file=html_filepath, auto_open=True)
print (f"Multivariate plot for {Variable}, WaterTemp, and DataSetClimate successfully saved to: {html_filepath}")

#%%
# 8.8. Frequency Distribution Of Anomaly Labels ==============================================================================================

# %%
