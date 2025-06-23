import pandas as pd
import json

def read_csv(file_path):
    """Reads a CSV file and returns a pandas DataFrame."""
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        return pd.DataFrame()

def write_csv(file_path, dataframe):
    """Writes a pandas DataFrame to a CSV file."""
    dataframe.to_csv(file_path, index=False)

def read_json(file_path):
    """Reads a JSON file and returns a dictionary."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def write_json(file_path, data):
    """Writes a dictionary to a JSON file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def save_report_as_markdown(report, filename):
    """Saves a string as a markdown file."""
    with open(filename, 'w') as f:
        f.write(report)
