import pandas as pd

def extract_full_cleaned_excel_table(file_path, sheet_name=None):
    # Read Excel file
    excel_data = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')

    # If sheet_name=None, read the first sheet from the dict
    if isinstance(excel_data, dict):
        # Get the first sheet's DataFrame
        df = list(excel_data.values())[0]
    else:
        df = excel_data

    # Clean column headers
    df.columns = [str(col).strip() for col in df.columns]

    # Drop fully empty rows
    df.dropna(how='all', inplace=True)

    # Reset index
    df.reset_index(drop=True, inplace=True)

    return df
# Example usage
if __name__ == "__main__":
    excel_file = "CANE2E_Testcases.xlsx"   # Replace with your Excel file path
    df = extract_full_cleaned_excel_table(excel_file)
    if df is not None:
        print(df.head())  # Print only first few rows
    else:
        print("No usable data found.")