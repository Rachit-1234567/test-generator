import PyPDF2
import pandas as pd
import re
from typing import Optional, List
import logging

# Configure logging for better debugging and error tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_active_requirements_table(pdf_path: str) -> Optional[pd.DataFrame]:
    """
    Extracts the Active Requirements table from a PDF file, handling multi-page tables
    and including version in the Unique ID.
    
    Args:
        pdf_path (str): Path to the PDF file.
    
    Returns:
        Optional[pd.DataFrame]: DataFrame containing the table data or None if not found.
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            capturing = False
            data: List[List[str]] = []
            headers = ['Unique ID', 'Name']  # Simplified to include version in Unique ID
            current_row: List[str] = []
            page_count = len(pdf_reader.pages)

            logging.info(f"Processing PDF with {page_count} pages")

            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                if not text:
                    logging.warning(f"Page {page_num} is empty or text could not be extracted")
                    continue

                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Detect start of Active Requirements table
                    if not capturing and re.search(r'\bActive\s+Requirements\b', line, re.IGNORECASE):
                        capturing = True
                        logging.info(f"Found Active Requirements table on page {page_num}")
                        continue

                    if capturing:
                        # Stop capturing at another major section heading
                        if re.match(r"^\d{1,2}\.\d+\s+|^[A-Z][a-zA-Z\s]+:", line):
                            capturing = False
                            logging.info(f"End of Active Requirements table detected on page {page_num}")
                            break

                        # Handle multi-line rows by accumulating text
                        if re.match(r"REQ-[\w-]+\s+v\d+", line):
                            # If we have a partial row, save it before starting a new one
                            if current_row:
                                if len(current_row) >= 2:
                                    data.append(current_row[:2])
                                current_row = []

                            # Match requirement ID with version and name
                            match = re.match(r"^(REQ-[\w-]+)\s+v(\d+)\s+(.+?)(?:\s+\(\w+\)\s*\d+)?$", line)
                            if match:
                                unique_id = f"{match.group(1)} v{match.group(2)}".strip()
                                name = match.group(3).strip()
                                current_row = [unique_id, name]
                            else:
                                logging.debug(f"Line on page {page_num} did not fully match: {line}")
                                current_row.append(line)
                        elif current_row:
                            # Append to the current row's name if it's a continuation
                            current_row[1] = (current_row[1] + " " + line).strip() if len(current_row) > 1 else line

                # Handle row that spans a page break
                if capturing and current_row and len(current_row) >= 2:
                    data.append(current_row[:2])
                    current_row = []

            # Finalize any remaining row
            if current_row and len(current_row) >= 2:
                data.append(current_row[:2])

            if data:
                df = pd.DataFrame(data, columns=headers)
                logging.info(f"Extracted {len(df)} rows from Active Requirements table")
                return df
            else:
                logging.warning("No matching table found in the PDF")
                return None

    except FileNotFoundError:
        logging.error(f"PDF file not found: {pdf_path}")
        return None
    except Exception as e:
        logging.error(f"An error occurred while processing the PDF: {str(e)}")
        return None

def save_to_csv(df: pd.DataFrame, output_path: str) -> None:
    """
    Saves the DataFrame to a CSV file.
    
    Args:
        df (pd.DataFrame): DataFrame to save.
        output_path (str): Path to save the CSV file.
    """
    try:
        df.to_csv(output_path, index=False)
        logging.info(f"Table saved to {output_path}")
    except Exception as e:
        logging.error(f"Failed to save CSV: {str(e)}")

if __name__ == "__main__":
    pdf_file = "CANE2EProtectionSpecification.v3.pdf"  # Replace with your actual PDF path
    output_csv = "active_requirements.csv"  # Output CSV file path

    df = extract_active_requirements_table(pdf_file)
    if df is not None:
        print("Extracted Active Requirements Table:")
        print(df)
        save_to_csv(df, output_csv)
    else:
        print("No table could be extracted.")