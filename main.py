import csv
from datetime import datetime, timedelta
import os
import json
from collections import defaultdict


def process_csv(input_file, output_folder, sort_column):
    """
    Processes a CSV file by:
      - Reading and parsing the data.
      - Sorting the data based on the sort_column.
      - Cleaning rows where Column D is "Student" or "Parent" by clearing values
        between columns "Number of Students" and the second occurrence of
        "Other (please specify in Notes)".
      - Standardizing Column F (Country) values using country_mappings.json.
      - Normalizing Column H (State) values for US rows or when a recognized US state is detected:
          * If Column F equals "United States", or if it's blank but Column H contains a recognized US state,
            then set the country to "United States" (if needed) and standardize the state.
          * This uses state_mappings.json to replace abbreviations with full names.
          * If the normalized state is "other - non-us", it is explicitly set to "Other - Non-US".
      - Clearing state cells that match a hard-coded list of bad entries.
      - **New Step:** If Country is blank and the City/Town (Column G) and State (Column H) are identical (and not both blank),
            then replace the state value with "Other - Non-US".
      - **New Step:** If the Country is not blank, not "United States", and the State cell contains a recognized US state,
            then clear the State cell.
      - Email and Domain Cleaning:
          * If an email address in Column A contains "@qq.com" (case-insensitive), set Column H to "Other - Non-US".
          * If Column J contains "dayofai.org" (case-insensitive), clear that cell.
      - Force Column H for rows where Country is "China".
      - Additional adjustment for @qq.com emails:
          * If the email (Column A) contains "@qq.com", Country (Column F) is "United States", and State (Column H) is "Other - Non-US",
            then set Country to "China" and clear Columns G and I.
      - Writing the full sorted-and-cleaned data to a CSV file.
      - Splitting and writing data into separate files based on date ranges.
    """
    try:
        # Load state mappings from state_mappings.json
        with open("state_mappings.json", "r", encoding="utf-8") as sm_file:
            state_mappings = json.load(sm_file)
        # Load country mappings from country_mappings.json
        with open("country_mappings.json", "r", encoding="utf-8") as cm_file:
            country_mappings = json.load(cm_file)

        with open(input_file, "r", newline="", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames

            if fieldnames is None:
                raise ValueError("No headers found in CSV file.")
            if sort_column not in fieldnames:
                raise ValueError(
                    f"Sort column '{sort_column}' not found in CSV headers"
                )

            data = []
            # Read and parse data, converting the sort_column to datetime
            for row in reader:
                try:
                    row[sort_column] = datetime.strptime(
                        row[sort_column], "%Y-%m-%d %H:%M:%S"
                    )
                    data.append(row)
                except ValueError as e:
                    print(
                        f"Error converting datetime in row: {row}. Skipping. Error: {e}"
                    )
                    continue

            # Sort data based on the datetime in sort_column
            sorted_data = sorted(data, key=lambda row: row[sort_column])

            # --- Cleaning Step: Remove values if Column D is "Student" or "Parent" ---
            if len(fieldnames) < 4:
                raise ValueError(
                    "CSV does not contain enough columns to check column D."
                )
            col_d_header = fieldnames[3]
            try:
                start_index = fieldnames.index("Number of Students")
            except ValueError:
                raise ValueError("Header 'Number of Students' not found.")
            other_indices = [
                i
                for i, header in enumerate(fieldnames)
                if header == "Other (please specify in Notes)"
            ]
            if len(other_indices) < 2:
                raise ValueError(
                    "Expected at least 2 occurrences of 'Other (please specify in Notes)', but found fewer."
                )
            end_index = other_indices[1]
            for row in sorted_data:
                if row[col_d_header].strip() in ["Student", "Parent"]:
                    for col in fieldnames[start_index : end_index + 1]:
                        row[col] = ""

            # --- Standardize Country Names using country_mappings ---
            if len(fieldnames) < 6:
                raise ValueError(
                    "CSV does not contain enough columns to check column F."
                )
            col_f_header = fieldnames[5]
            for row in sorted_data:
                country = row[col_f_header].strip()
                found_mapping = None
                for key, value in country_mappings.items():
                    if key.lower() == country.lower():
                        found_mapping = value
                        break
                if found_mapping is not None:
                    row[col_f_header] = found_mapping

            # --- Normalizing Column H Values for US States and Inferring Country if Needed ---
            if len(fieldnames) < 8:
                raise ValueError(
                    "CSV does not contain enough columns to check column H."
                )
            col_h_header = fieldnames[7]
            # Build a set of recognized US state identifiers (abbreviations and full names) from state_mappings
            valid_states_all = set()
            for k, v in state_mappings.items():
                valid_states_all.add(k.lower())
                valid_states_all.add(v.lower())
            for row in sorted_data:
                country_val = row[col_f_header].strip()
                state_val = row[col_h_header].strip().lower()
                if country_val == "United States" or (
                    country_val == "" and state_val in valid_states_all
                ):
                    if country_val == "":
                        row[col_f_header] = "United States"
                    if state_val in state_mappings:
                        normalized_state = state_mappings[state_val]
                    else:
                        normalized_state = state_val
                    # Ensure proper capitalization for "Other - Non-US"
                    if normalized_state.lower() == "other - non-us":
                        normalized_state = "Other - Non-US"
                        row[col_f_header] = ""
                    else:
                        normalized_state = normalized_state.title()
                    row[col_h_header] = normalized_state

            # --- Clear Bad State Entries ---
            bad_state_entries = {
                "1",
                ".",
                "'- Select -'",
                "'-- Bitte auswählen (nur für USA / Kan. / Aus.)",
                "'- Select -",
                "Choose a State or Province",
                "N/A",
                "n/a",
                "Not Applicable",
                "Not Specified",
                "Not US or Canada",
                "Others",
                "Select State",
            }
            for row in sorted_data:
                if row[col_h_header].strip() in bad_state_entries:
                    row[col_h_header] = ""

            # --- Handle Blank Country with Matching City/Town and State ---
            col_g_header = fieldnames[6]  # City/Town
            for row in sorted_data:
                if row[col_f_header].strip() == "":
                    city = row[col_g_header].strip()
                    state = row[col_h_header].strip()
                    if city and state and city.lower() == state.lower():
                        row[col_h_header] = "Other - Non-US"

            # --- NEW STEP: Clear US State if Country is not United States ---
            # If Country is not blank and not "United States", and the State cell contains a recognized US state, clear the state.
            for row in sorted_data:
                country_val = row[col_f_header].strip()
                state_val = row[col_h_header].strip().lower()
                if (
                    country_val
                    and country_val != "United States"
                    and state_val in valid_states_all
                ):
                    row[col_h_header] = ""

            # --- Email and Domain Cleaning ---
            col_a_header = fieldnames[0]  # Email Address (Column A)
            col_j_header = fieldnames[9] if len(fieldnames) > 9 else None
            for row in sorted_data:
                email = row[col_a_header].strip()
                if "@qq.com" in email.lower():
                    row[col_h_header] = "Other - Non-US"
                if col_j_header:
                    if "dayofai.org" in row[col_j_header].strip().lower():
                        row[col_j_header] = ""

            # --- Force Column H for rows where Country is China ---
            for row in sorted_data:
                if row[col_f_header].strip() == "China":
                    row[col_h_header] = "Other - Non-US"

            # --- Additional Adjustment for @qq.com emails ---
            col_i_header = fieldnames[8]  # Zip Code (Column I)
            for row in sorted_data:
                email = row[col_a_header].strip()
                if (
                    "@qq.com" in email.lower()
                    and row[col_f_header].strip() == "United States"
                    and row[col_h_header].strip() == "Other - Non-US"
                ):
                    row[col_f_header] = "China"
                    row[col_g_header] = ""
                    row[col_i_header] = ""

            # --- Create mapping of date ranges ---
            date_ranges = defaultdict(list)
            for row in sorted_data:
                date = row[sort_column]
                if date < datetime(2024, 10, 15):
                    date_ranges["1-pre1015.csv"].append(row)
                elif datetime(2024, 10, 15) <= date < datetime(2024, 11, 1):
                    date_ranges["2-1031.csv"].append(row)
                else:
                    key = f"{date.year}-{date.month:02d}"
                    date_ranges[key].append(row)

            # --- Write the full sorted and cleaned data to "0-sorted-and-cleaned.csv" ---
            sorted_cleaned_filename = "0-sorted-and-cleaned.csv"
            with open(
                os.path.join(output_folder, sorted_cleaned_filename),
                "w",
                newline="",
                encoding="utf-8",
            ) as outfile:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in sorted_data:
                    row_to_write = row.copy()
                    row_to_write[sort_column] = row_to_write[sort_column].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    writer.writerow(row_to_write)

            # --- Process special files ---
            for special_file in ["1-pre1015.csv", "2-1031.csv"]:
                if date_ranges[special_file]:
                    with open(
                        os.path.join(output_folder, special_file),
                        "w",
                        newline="",
                        encoding="utf-8",
                    ) as outfile:
                        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                        writer.writeheader()
                        for row in date_ranges[special_file]:
                            row_to_write = row.copy()
                            row_to_write[sort_column] = row_to_write[
                                sort_column
                            ].strftime("%Y-%m-%d %H:%M:%S")
                            writer.writerow(row_to_write)

            # --- Process monthly files starting with index 3 ---
            monthly_dates = sorted(
                [
                    k
                    for k in date_ranges.keys()
                    if k not in ["1-pre1015.csv", "2-1031.csv"]
                ]
            )
            for index, month_key in enumerate(monthly_dates, start=3):
                filename = f"{index}-{month_key}.csv"
                with open(
                    os.path.join(output_folder, filename),
                    "w",
                    newline="",
                    encoding="utf-8",
                ) as outfile:
                    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in date_ranges[month_key]:
                        row_to_write = row.copy()
                        row_to_write[sort_column] = row_to_write[sort_column].strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        writer.writerow(row_to_write)

    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
    except PermissionError:
        print("Error: Permission denied when accessing files.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    input_csv = "raw.csv"
    output_folder = "outputs"
    sort_column_name = "OPTIN_TIME"

    os.makedirs(output_folder, exist_ok=True)
    process_csv(input_csv, output_folder, sort_column_name)
    print(f"Data processed and saved to '{output_folder}'")
