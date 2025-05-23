import csv
from datetime import datetime
import os
import json
from collections import defaultdict
import unicodedata
from analysis_outputs import run_all_analyses


def remove_accents(input_str):
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", input_str)
        if not unicodedata.combining(c)
    )


def process_csv(input_file, output_folder, sort_column):
    try:
        # Load mapping files and lists for cleaning
        with open("state_mappings.json", "r", encoding="utf-8") as sm_file:
            state_mappings = json.load(sm_file)
        with open("country_mappings.json", "r", encoding="utf-8") as cm_file:
            country_mappings = json.load(cm_file)
        with open("bad_state_entries.json", "r", encoding="utf-8") as bse_file:
            bad_state_entries = set(json.load(bse_file))
        with open("bad_city_entries.json", "r", encoding="utf-8") as bce_file:
            raw_bad_cities = json.load(bce_file)
            bad_city_entries = set(entry.strip().lower() for entry in raw_bad_cities)
        with open("bad_school_entries.json", "r", encoding="utf-8") as bs_file:
            raw_bad_schools = json.load(bs_file)
            bad_school_entries = set(entry.strip().lower() for entry in raw_bad_schools)
        with open("city_to_country.json", "r", encoding="utf-8") as ctc_file:
            city_to_country = json.load(ctc_file)
        with open("city_corrections.json", "r", encoding="utf-8") as cc_file:
            raw = json.load(cc_file)
            city_corrections = {k.strip().lower(): v for k, v in raw.items()}

        # Read input CSV
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
                    # Use "Entry Date" if available; otherwise, use sort_column.
                    if "Entry Date" in row and row["Entry Date"].strip():
                        sort_date = datetime.strptime(
                            row["Entry Date"].strip(), "%Y-%m-%d"
                        )
                    else:
                        sort_date = datetime.strptime(
                            row[sort_column].strip(), "%Y-%m-%d %H:%M:%S"
                        )
                    row[sort_column] = sort_date
                    data.append(row)
                except ValueError as e:
                    print(
                        f"Error converting datetime in row: {row}. Skipping. Error: {e}"
                    )
                    continue

            sorted_data = sorted(data, key=lambda row: row[sort_column])

            # === Cleaning Steps (unchanged) ===
            col_d_header = fieldnames[3]  # "I am a..."
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

            for row in sorted_data:
                city = row[fieldnames[6]].strip()
                if city:
                    city_lower = city.lower()
                    if city_lower in city_to_country:
                        row[col_f_header] = city_to_country[city_lower]

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
            for row in sorted_data:
                if row[col_h_header].strip() in bad_state_entries:
                    row[col_h_header] = ""

            col_g_header = fieldnames[6]  # City/Town
            for row in sorted_data:
                city_norm = row[col_g_header].strip().lower()
                if city_norm in bad_city_entries:
                    row[col_g_header] = ""
            for row in sorted_data:
                city = row[col_g_header].strip()
                if city.isdigit():
                    row[col_g_header] = ""

            for row in sorted_data:
                city = row[col_g_header].strip()
                if city:
                    row[col_g_header] = remove_accents(city)

            for row in sorted_data:
                city = row[col_g_header].strip()
                key = city.lower()
                if key in city_corrections:
                    row[col_g_header] = city_corrections[key]

            col_e_header = fieldnames[4]
            for row in sorted_data:
                school = row[col_e_header].strip()
                if school.isdigit():
                    row[col_e_header] = ""
                elif school.lower() in bad_school_entries:
                    row[col_e_header] = ""

            for row in sorted_data:
                if row[col_f_header].strip() == "":
                    city = row[col_g_header].strip()
                    state = row[col_h_header].strip()
                    if city and state and city.lower() == state.lower():
                        row[col_h_header] = ""
            for row in sorted_data:
                country_val = row[col_f_header].strip()
                if country_val and country_val != "United States":
                    city = row[col_g_header].strip()
                    state = row[col_h_header].strip()
                    if city and state and city.lower() == state.lower():
                        row[col_h_header] = ""
            for row in sorted_data:
                country_val = row[col_f_header].strip()
                state_val = row[col_h_header].strip().lower()
                if (
                    country_val
                    and country_val != "United States"
                    and state_val in valid_states_all
                ):
                    row[col_h_header] = ""
            for row in sorted_data:
                if row[col_f_header].strip() == "United States":
                    city = row[col_g_header].strip()
                    state = row[col_h_header].strip()
                    if city.lower() == "new york" and state.lower() == "new york":
                        row[col_h_header] = "New York"

            col_a_header = fieldnames[0]  # Email Address
            col_j_header = fieldnames[9] if len(fieldnames) > 9 else None
            for row in sorted_data:
                email = row[col_a_header].strip()
                if "@qq.com" in email.lower():
                    row[col_h_header] = ""
                if col_j_header and "dayofai.org" in row[col_j_header].strip().lower():
                    row[col_j_header] = ""
            for row in sorted_data:
                if row[col_f_header].strip() == "China":
                    row[col_h_header] = ""
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
            for row in sorted_data:
                if row[col_h_header].strip().lower() == "other - non-us":
                    row[col_h_header] = ""

            cols_to_clear = [
                "Preschool",
                "Early elementary K - 2 (5 - 7 years)",
                "Upper elementary 3 - 5 (8 - 10 years)",
                "Middle school 6 - 8 (11 - 13 years)",
                "High school 9 - 12 (14 - 17 years)",
                "Post-secondary school/community college (18+)",
                "College or university",
                "Adult or vocational education",
            ]
            role_header = fieldnames[3]  # "I am a..."
            teach_status_header = "I don't teach at the moment"
            for row in sorted_data:
                if (
                    row[role_header].strip() == "Teacher / Educator"
                    and row.get(teach_status_header, "").strip()
                    == "I don't teach at the moment"
                ):
                    for col in cols_to_clear:
                        if col in row:
                            row[col] = ""

            computed_grade_header = "Computed Grade Band"
            try:
                col_p_index = fieldnames.index("High school 9 - 12 (14 - 17 years)")
            except ValueError:
                raise ValueError(
                    "Header 'High school 9 - 12 (14 - 17 years)' not found."
                )
            if computed_grade_header not in fieldnames:
                fieldnames.insert(col_p_index + 1, computed_grade_header)

            def compute_grade_band(row):
                colL = row.get("Preschool", "").strip()
                colM = row.get("Early elementary K - 2 (5 - 7 years)", "").strip()
                colN = row.get("Upper elementary 3 - 5 (8 - 10 years)", "").strip()
                colO = row.get("Middle school 6 - 8 (11 - 13 years)", "").strip()
                colP = row.get("High school 9 - 12 (14 - 17 years)", "").strip()
                band = ""
                if colL:
                    band += "PK"
                if colM:
                    band += ", K-2" if band else "K-2"
                if colN:
                    band += ", 3-5" if band else "3-5"
                if colO:
                    band += ", 6-8" if band else "6-8"
                if colP:
                    band += ", 9-12" if band else "9-12"
                return band

            for row in sorted_data:
                row[computed_grade_header] = compute_grade_band(row)

            computed_stem_header = "Computed STEM/Tech/Non-STEM"
            try:
                col_bi_index = fieldnames.index("Cultural education")
            except ValueError:
                raise ValueError("Header 'Cultural education' not found.")
            if computed_stem_header not in fieldnames:
                fieldnames.insert(col_bi_index + 1, computed_stem_header)

            def compute_stem_tech_nonstem(row):
                if (
                    row.get("I am a...", "").strip()
                    and row.get("I don't teach at the moment", "").strip()
                ):
                    return ""
                tech_cols = [
                    "Computer science",
                    "Robotics",
                    "Career and technical education",
                    "Digital/Information Literacy",
                ]
                stem_cols = [
                    "Chemistry",
                    "Mathematics",
                    "Physics",
                    "Biology",
                    "Science",
                    "Engineering",
                    "Environmental",
                ]
                non_stem_cols = [
                    "Social studies",
                    "Business",
                    "Economics",
                    "Journalism",
                    "Humanities",
                    "Art",
                    "Dance",
                    "Music",
                    "English",
                    "Language (other than English)",
                    "Foreign languages",
                    "Literature",
                    "Performing arts",
                    "Physical education",
                    "Civics education",
                    "Health education",
                    "Vocational education",
                    "Agricultural education",
                    "Legal education",
                    "Maritime education",
                    "Military education and training",
                    "Teacher education",
                    "Veterinary education",
                    "Library Media",
                    "Librarian",
                    "Special education",
                    "Deaf education",
                    "Cultural education",
                ]
                selected = []
                if any(row.get(col, "").strip() for col in tech_cols):
                    selected.append("Technology")
                if any(row.get(col, "").strip() for col in stem_cols):
                    selected.append("STEM")
                if any(row.get(col, "").strip() for col in non_stem_cols):
                    selected.append("Non-STEM")
                return ", ".join(selected)

            for row in sorted_data:
                row[computed_stem_header] = compute_stem_tech_nonstem(row)

            # ==== US/International city+state clearing logic (name, asciiname, alternatenames) ====
            us_city_state_set = set()
            intl_city_country_set = set()
            with open("all_cities.csv", "r", encoding="utf-8") as acf:
                ac_reader = csv.DictReader(acf)
                for city_row in ac_reader:
                    country = city_row["country"].strip()
                    states = city_row.get("state(s)", "").strip()
                    # Gather all possible normalized city names (name, asciiname, alternatenames)
                    city_names = set()
                    for col in ["name", "asciiname", "alternatenames"]:
                        value = city_row.get(col, "")
                        if value:
                            if col == "alternatenames":
                                for alt in value.split(","):
                                    city_names.add(remove_accents(alt.strip()).lower())
                            else:
                                city_names.add(remove_accents(value.strip()).lower())

                    if country == "United States":
                        if states:
                            for st in states.split("|"):
                                state_clean = remove_accents(st.strip()).lower()
                                for city_name in city_names:
                                    if city_name:
                                        us_city_state_set.add(
                                            (country, state_clean, city_name)
                                        )
                    else:
                        for city_name in city_names:
                            if city_name:
                                intl_city_country_set.add((country, city_name))

            # Apply the clearing logic per row
            for row in sorted_data:
                country = row.get("Country", "").strip()
                city = remove_accents(row.get("City/Town", "")).strip().lower()
                state = remove_accents(row.get("State", "")).strip().lower()
                if not country or not city:
                    continue
                if country == "United States":
                    if (country, state, city) in us_city_state_set:
                        row["City/Town"] = ""
                else:
                    if (country, city) in intl_city_country_set:
                        row["City/Town"] = ""
                        row["State"] = ""

            # STEP 8: Remove unwanted columns.
            deletion_set = {
                "Created By (User Id)",
                "Entry Id",
                "Date Updated",
                "Transaction Id",
                "Payment Amount",
                "Payment Date",
                "Payment Status",
                "Post Id",
                "User Agent",
                "User IP",
                "Name (Prefix)",
                "Name (Middle)",
                "MEMBER_RATING",
                "OPTIN_IP",
                "CONFIRM_TIME",
                "CONFIRM_IP",
                "LATITUDE",
                "LONGITUDE",
                "GMTOFF",
                "DSTOFF",
                "TIMEZONE",
                "CC",
                "REGION",
                "LAST_CHANGED",
                "LEID",
                "EUID",
                "TAGS",
                "Other (please specify in Notes)",
            }
            deletion_set.add("NOTES")
            fieldnames = [header for header in fieldnames if header not in deletion_set]
            for row in sorted_data:
                for key in list(row.keys()):
                    if key in deletion_set:
                        del row[key]

            # STEP 9: Reorder columns into the desired final order.
            desired_order = [
                "Email Address",
                "Name (First)",
                "Name (Last)",
                "I am a...",
                "Referral Source",
                "School / Company Name",
                "Country",
                "City/Town",
                "State",
                "Zip Code",
                "Website",
                "Number of Students",
                "I don't teach at the moment",
                "Computed Grade Band",
                "Computed STEM/Tech/Non-STEM",
                "Notes",
                "Preschool",
                "Early elementary K - 2 (5 - 7 years)",
                "Upper elementary 3 - 5 (8 - 10 years)",
                "Middle school 6 - 8 (11 - 13 years)",
                "High school 9 - 12 (14 - 17 years)",
                "Post-secondary school/community college (18+)",
                "College or university",
                "Adult or vocational education",
                "Computer science",
                "Robotics",
                "Chemistry",
                "Mathematics",
                "Physics",
                "Biology",
                "Science",
                "Engineering",
                "Environmental",
                "Social studies",
                "Business",
                "Economics",
                "Journalism",
                "Humanities",
                "Art",
                "Dance",
                "Music",
                "English",
                "Language (other than English)",
                "Foreign languages",
                "Literature",
                "Performing arts",
                "Physical education",
                "Civics education",
                "Health education",
                "Vocational education",
                "Agricultural education",
                "Career and technical education",
                "Legal education",
                "Maritime education",
                "Military education and training",
                "Teacher education",
                "Veterinary education",
                "Library Media",
                "Librarian",
                "Digital/Information Literacy",
                "Special education",
                "Deaf education",
                "Cultural education",
                "Day of AI",
                "MIT RAISE",
                "Interested in research participation",
                "Source Url",
                "Entry Date",
                "OPTIN_TIME",
            ]
            fieldnames = desired_order

            # Write the cleaned data to output CSV files (with date-range splits).
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

            # (Optional) You can still save unsure_rows here if you kept that step

        run_all_analyses(sorted_data, output_folder)

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
