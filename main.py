import csv
from datetime import datetime
import os
import json
import re
from collections import defaultdict


def process_csv(input_file, output_folder, sort_column):
    """
    Processes a CSV file by:
      - Reading and parsing the data.
      - Sorting the data based on the sort_column.
      - Cleaning rows where Column D is "Student" or "Parent" by clearing values
        between "Number of Students" and the second occurrence of "Other (please specify in Notes)".
      - Standardizing Column F (Country) values using country_mappings.json.
      - Normalizing Column H (State) values for US rows or when a recognized US state is detected:
          * If Column F equals "United States", or if it's blank but Column H contains a recognized US state,
            then set the country to "United States" (if needed) and standardize the state using state_mappings.json.
          * If the normalized state is "other - non-us", the State cell is set to blank.
      - Clearing state cells that match a list of bad entries loaded from bad_state_entries.json.
      - NEW STEP 0.5: Clear bad city entries in Column G using bad_city_entries.json.
      - NEW STEP 0.6: Clear City/Town (Column G) if it is purely numeric.
      - NEW STEP 0.7: Clear School/Company Name (Column E) if it is purely numeric or if it matches bad school entries (loaded from bad_school_entries.json).
      - NEW STEP 1: If Country is blank and City/Town (Column G) equals State (Column H) (ignoring case), clear the State cell.
      - NEW STEP 2: For non-blank countries (except New York/New York for US), if City/Town equals State (ignoring case), clear the State cell.
      - NEW STEP 3: If Country is not blank and not "United States" and the State cell contains a recognized US state,
            clear the State cell.
      - NEW STEP 4: Preserve New York if Country is "United States" and both City/Town and State equal "New York".
      - Email and Domain Cleaning:
          * If an email address in Column A contains "@qq.com" (case-insensitive), set Column H to blank.
          * If Column J contains "dayofai.org" (case-insensitive), clear that cell.
      - Force Column H for rows where Country is "China": set Column H to blank.
      - Additional adjustment for @qq.com emails:
          * If the email in Column A contains "@qq.com", Column F is "United States", and Column H is blank,
            then set Column F to "China" and clear Columns G and I.
      - FINAL CLEAN-UP: Remove any residual "Other - Non-US" in Column H.
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
        # Load bad state entries from bad_state_entries.json
        with open("bad_state_entries.json", "r", encoding="utf-8") as bse_file:
            bad_state_entries = set(json.load(bse_file))
        # Load bad city entries from bad_city_entries.json and lower-case them
        with open("bad_city_entries.json", "r", encoding="utf-8") as bce_file:
            raw_bad_cities = json.load(bce_file)
            bad_city_entries = set(entry.strip().lower() for entry in raw_bad_cities)
        # Load bad school entries from bad_school_entries.json and lower-case them
        with open("bad_school_entries.json", "r", encoding="utf-8") as bs_file:
            raw_bad_schools = json.load(bs_file)
            bad_school_entries = set(entry.strip().lower() for entry in raw_bad_schools)

        with open(input_file, "r", newline="", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames
            if not fieldnames:
                raise ValueError("No headers found in CSV file.")
            if sort_column not in fieldnames:
                raise ValueError(
                    f"Sort column '{sort_column}' not found in CSV headers"
                )

            data = []
            for row in reader:
                try:
                    # Use "Entry Date" if it exists and is non-empty; otherwise, use OPTIN_TIME.
                    if "Entry Date" in row and row["Entry Date"].strip():
                        # Parse Entry Date (which is in "YYYY-MM-DD" format)
                        sort_date = datetime.strptime(
                            row["Entry Date"].strip(), "%Y-%m-%d"
                        )
                    else:
                        # Parse OPTIN_TIME (which is in "YYYY-MM-DD HH:MM:SS" format)
                        sort_date = datetime.strptime(
                            row[sort_column].strip(), "%Y-%m-%d %H:%M:%S"
                        )
                    # Override the sort column with the computed date so later steps use it.
                    row[sort_column] = sort_date
                    data.append(row)
                except ValueError as e:
                    print(
                        f"Error converting datetime in row: {row}. Skipping. Error: {e}"
                    )
                    continue

            sorted_data = sorted(data, key=lambda row: row[sort_column])

            # --- Cleaning Step: Remove values if Column D is "Student" or "Parent" ---
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
            col_f_header = fieldnames[5]  # Country
            for row in sorted_data:
                country = row[col_f_header].strip()
                found_mapping = None
                for key, value in country_mappings.items():
                    if key.lower() == country.lower():
                        found_mapping = value
                        break
                if found_mapping is not None:
                    row[col_f_header] = found_mapping

            # --- Normalizing Column H (State) for US States and Inferring Country if Needed ---
            col_h_header = fieldnames[7]  # State
            valid_states_all = set()
            for k, v in state_mappings.items():
                valid_states_all.add(k.lower())
                valid_states_all.add(v.lower())
            valid_states_all.add("district of columbia")
            for row in sorted_data:
                country_val = row[col_f_header].strip()
                state_val = row[col_h_header].strip().lower()
                if country_val == "United States" or (
                    country_val == "" and state_val in valid_states_all
                ):
                    if country_val == "":
                        row[col_f_header] = "United States"
                    normalized_state = state_mappings.get(state_val, state_val)
                    if normalized_state.lower() == "other - non-us":
                        normalized_state = ""
                        row[col_f_header] = ""
                    else:
                        normalized_state = normalized_state.title()
                    row[col_h_header] = normalized_state

            # --- Clear Bad State Entries ---
            for row in sorted_data:
                if row[col_h_header].strip() in bad_state_entries:
                    row[col_h_header] = ""

            # --- NEW STEP 0.5: Clear Bad City Entries ---
            col_g_header = fieldnames[6]  # City/Town
            for row in sorted_data:
                city_norm = row[col_g_header].strip().lower()
                if city_norm in bad_city_entries:
                    row[col_g_header] = ""

            # --- NEW STEP 0.6: Clear City/Town if it is just numeric ---
            for row in sorted_data:
                city = row[col_g_header].strip()
                if city.isdigit():
                    row[col_g_header] = ""

            # --- NEW STEP 0.7: Clear School/Company Name if it is just numeric or matches bad school entries ---
            col_e_header = fieldnames[4]  # School / Company Name
            for row in sorted_data:
                school = row[col_e_header].strip()
                if school.isdigit():
                    row[col_e_header] = ""
                elif school.lower() in bad_school_entries:
                    row[col_e_header] = ""

            # --- NEW STEP 1: Clear State if City/Town equals State (ignoring case) for blank Country ---
            for row in sorted_data:
                if row[col_f_header].strip() == "":
                    city = row[col_g_header].strip()
                    state = row[col_h_header].strip()
                    if city and state and city.lower() == state.lower():
                        row[col_h_header] = ""

            # --- NEW STEP 2: For non-blank countries (except New York/New York for US),
            # if City/Town equals State (ignoring case), then clear the State cell.
            for row in sorted_data:
                country_val = row[col_f_header].strip()
                if country_val and country_val != "United States":
                    city = row[col_g_header].strip()
                    state = row[col_h_header].strip()
                    if city and state and city.lower() == state.lower():
                        row[col_h_header] = ""

            # --- NEW STEP 3: Clear US State for Non-US Country ---
            for row in sorted_data:
                country_val = row[col_f_header].strip()
                state_val = row[col_h_header].strip().lower()
                if (
                    country_val
                    and country_val != "United States"
                    and state_val in valid_states_all
                ):
                    row[col_h_header] = ""

            # --- NEW STEP 4: Preserve New York if Country is United States and both City/Town and State are New York ---
            for row in sorted_data:
                if row[col_f_header].strip() == "United States":
                    city = row[col_g_header].strip()
                    state = row[col_h_header].strip()
                    if city.lower() == "new york" and state.lower() == "new york":
                        row[col_h_header] = "New York"

            # --- Email and Domain Cleaning ---
            col_a_header = fieldnames[0]  # Email Address
            col_j_header = fieldnames[9] if len(fieldnames) > 9 else None
            for row in sorted_data:
                email = row[col_a_header].strip()
                if "@qq.com" in email.lower():
                    row[col_h_header] = ""
                if col_j_header and "dayofai.org" in row[col_j_header].strip().lower():
                    row[col_j_header] = ""

            # --- Force Column H for rows where Country is China ---
            for row in sorted_data:
                if row[col_f_header].strip() == "China":
                    row[col_h_header] = ""

            # --- Additional Adjustment for @qq.com emails ---
            col_i_header = fieldnames[8]  # Zip Code
            for row in sorted_data:
                email = row[col_a_header].strip()
                if (
                    "@qq.com" in email.lower()
                    and row[col_f_header].strip() == "United States"
                    and row[col_h_header].strip() == ""
                ):
                    row[col_f_header] = "China"
                    row[col_g_header] = ""
                    row[col_i_header] = ""

            # --- FINAL CLEAN-UP: Remove any residual "Other - Non-US" ---
            for row in sorted_data:
                if row[col_h_header].strip().lower() == "other - non-us":
                    row[col_h_header] = ""

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
