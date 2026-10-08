import sys
import pandas as pd


def extract_anomaly_windows(input_file, output_file, anomaly_column, buffer):
    # Read the CSV
    df = pd.read_csv(input_file)

    # Find row positions where the anomaly column is True
    anomaly_positions = df.index[(df[anomaly_column] == True) | (df[anomaly_column].isna())].tolist()

    if not anomaly_positions:
        print("No anomalies found.")
        return

    windows = []

    # Start with the first anomaly
    window_start = max(0, anomaly_positions[0] - buffer)
    window_end = min(len(df) - 1, anomaly_positions[0] + buffer)

    for pos in anomaly_positions[1:]:

        # If this anomaly falls within the current window,
        # extend the window to include its buffer.
        if pos <= window_end:
            window_end = min(len(df) - 1, pos + buffer)

        # Otherwise, save the current window and start a new one
        else:
            windows.append((window_start, window_end))

            window_start = max(0, pos - buffer)
            window_end = min(len(df) - 1, pos + buffer)

    # Add the final window
    windows.append((window_start, window_end))

    # Build output with an empty row after each window
    output_parts = []

    for start, end in windows:
        # Add the anomaly window
        output_parts.append(df.iloc[start:end + 1])

        # Add an empty row
        empty_row = pd.DataFrame(
            [["##########"] * len(df.columns)],
            columns=df.columns
        )
        output_parts.append(empty_row)

    # Combine everything
    output_df = pd.concat(output_parts, ignore_index=True)

    # Export
    output_df.to_csv(output_file, index=False)

    print(f"Found {len(anomaly_positions)} anomalous rows.")
    print(f"Created {len(windows)} anomaly windows.")
    print(f"Exported {len(output_df)} rows to {output_file}")


if __name__ == "__main__":
    extract_anomaly_windows(
        input_file=sys.argv[1],
        output_file=sys.argv[2],
        anomaly_column=sys.argv[3],
        buffer=3
    )