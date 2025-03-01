import csv
from datetime import datetime
import os
import json
from collections import defaultdict


def process_csv(input_file, output_folder, sort_column):
    """
    Processes the CSV file by performing cleaning, computed‐column insertion,
    unwanted column removal, column reordering, and splitting by date ranges.
    Then, it generates several analysis CSV files:

      1. all_registrations_by_country.csv – counts by Country.
      2. US_registrations_by_state.csv – counts by State for rows where Country is "United States".
      3. all_registrations_by_role.csv – counts by "I am a..." (role).
      4. all_registrations_computed_grade_bands.csv – counts by "Computed Grade Band".
      5. all_registrations_computed_subject_categories.csv – counts by "Computed STEM/Tech/Non-STEM".
      6. US_teachers_by_state.csv – counts by State for US teachers.
      7. US_teachers_computed_grade_bands.csv – counts by "Computed Grade Band" for US teachers.
      8. US_teachers_computed_subject_categories.csv – counts by "Computed STEM/Tech/Non-STEM" for US teachers.
      9. US_registrations_by_role.csv – counts by "I am a..." for rows with Country "United States".
     10. all_schools_locations.csv – unique schools with Country, City/Town, and State (sorted ascending by Country).

    For all analysis CSVs (except all_schools_locations.csv) a TOTAL row is appended.
    """
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
        # Load the City-to-Country mapping (keys are all lowercase)
        with open("city_to_country.json", "r", encoding="utf-8") as ctc_file:
            city_to_country = json.load(ctc_file)

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

            # === Cleaning Steps (NEW STEP 0.5 through NEW STEP 5) ===
            # Remove values between "Number of Students" and second "Other (please specify in Notes)"
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

            # Standardize Country using country_mappings.json.
            col_f_header = fieldnames[5]  # Country
            for row in sorted_data:
                country = row[col_f_header].strip()
                found_mapping = None
                for key, value in country_mappings.items():
                    if key.lower() == country.lower():
                        found_mapping = value
                        break
                if found_mapping is not None:
                    row[col_f_header] = found_mapping.title()

            # NEW: If Country is blank, use city_to_country mapping.
            for row in sorted_data:
                if row[col_f_header].strip() == "":
                    city = row[fieldnames[6]].strip()  # City/Town is column G
                    if city:
                        city_lower = city.lower()
                        if city_lower in city_to_country:
                            row[col_f_header] = city_to_country[city_lower].title()

            # Optional: Ensure all non-empty Country values are title-cased.
            for row in sorted_data:
                if row[col_f_header].strip():
                    row[col_f_header] = row[col_f_header].strip().title()

            # NEW STEP: Apply city_to_country mapping to all rows (not just blank countries).
            # If the cleaned City/Town value matches a key in the mapping,
            # update the Country field accordingly.
            for row in sorted_data:
                city = row[fieldnames[6]].strip()  # City/Town is column G
                if city:
                    city_lower = city.lower()
                    if city_lower in city_to_country:
                        row[col_f_header] = city_to_country[city_lower].title()

            # Normalize State using state_mappings.json.
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

            # Clean City/Town column.
            col_g_header = fieldnames[6]  # City/Town
            for row in sorted_data:
                city_norm = row[col_g_header].strip().lower()
                if city_norm in bad_city_entries:
                    row[col_g_header] = ""
            for row in sorted_data:
                city = row[col_g_header].strip()
                if city.isdigit():
                    row[col_g_header] = ""

            # Clean School / Company Name.
            col_e_header = fieldnames[4]
            for row in sorted_data:
                school = row[col_e_header].strip()
                if school.isdigit():
                    row[col_e_header] = ""
                elif school.lower() in bad_school_entries:
                    row[col_e_header] = ""

            # Additional cleaning for blank Country and State conditions.
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

            # Email and Domain Cleaning.
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

            # NEW STEP 5: Clear specific columns for teachers not teaching.
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

            # NEW STEP 6: Compute and insert the "Computed Grade Band" column after column P.
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

            # NEW STEP 7: Compute and insert the "Computed STEM/Tech/Non-STEM" column after column BI.
            computed_stem_header = "Computed STEM/Tech/Non-STEM"
            try:
                col_bi_index = fieldnames.index("Cultural education")
            except ValueError:
                raise ValueError("Header 'Cultural education' not found.")
            if computed_stem_header not in fieldnames:
                fieldnames.insert(col_bi_index + 1, computed_stem_header)

            def compute_stem_tech_nonstem(row):
                # If both "I am a..." and "I don't teach at the moment" contain values, return blank.
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

            # NEW STEP 8: Remove unwanted columns.
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
            deletion_set.add("NOTES")  # Remove headers that are exactly "NOTES"
            fieldnames = [header for header in fieldnames if header not in deletion_set]
            for row in sorted_data:
                for key in list(row.keys()):
                    if key in deletion_set:
                        del row[key]

            # NEW STEP 9: Reorder columns into the desired final order.
            desired_order = [
                "Email Address",
                "Name (First)",
                "Name (Last)",
                "I am a...",
                "School / Company Name",
                "Country",
                "City/Town",
                "State",
                "Zip Code",
                "Website",
                "Number of Students",
                "I don't teach at the moment",  # moved immediately after Number of Students
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

            # ============================================================
            # Analysis Outputs
            # ============================================================

            # 1. all_registrations_by_country.csv
            country_count = defaultdict(int)
            for row in sorted_data:
                country = row.get("Country", "").strip()
                country_count[country] += 1
            sorted_country = sorted(
                country_count.items(), key=lambda x: x[1], reverse=True
            )
            total = sum(count for _, count in sorted_country)
            with open(
                os.path.join(output_folder, "all_registrations_by_country.csv"),
                "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(["Country", "Count"])
                for country, count in sorted_country:
                    writer.writerow([country, count])
                writer.writerow(["TOTAL", total])

            # 2. US_registrations_by_state.csv
            us_state_count = defaultdict(int)
            for row in sorted_data:
                if row.get("Country", "").strip() == "United States":
                    state = row.get("State", "").strip()
                    us_state_count[state] += 1
            sorted_us_state = sorted(
                us_state_count.items(), key=lambda x: x[1], reverse=True
            )
            total = sum(count for _, count in sorted_us_state)
            with open(
                os.path.join(output_folder, "US_registrations_by_state.csv"),
                "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(["State", "Count"])
                for state, count in sorted_us_state:
                    writer.writerow([state, count])
                writer.writerow(["TOTAL", total])

            # 3a. all_registrations_by_role.csv
            role_count = defaultdict(int)
            for row in sorted_data:
                role = row.get("I am a...", "").strip()
                role_count[role] += 1
            sorted_role = sorted(role_count.items(), key=lambda x: x[1], reverse=True)
            total = sum(count for _, count in sorted_role)
            with open(
                os.path.join(output_folder, "all_registrations_by_role.csv"),
                "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(["Role", "Count"])
                for role, count in sorted_role:
                    writer.writerow([role, count])
                writer.writerow(["TOTAL", total])

            # 3b. all_registrations_computed_grade_bands.csv
            grade_band_count = defaultdict(int)
            for row in sorted_data:
                grade = row.get("Computed Grade Band", "").strip()
                grade_band_count[grade] += 1
            sorted_grade = sorted(
                grade_band_count.items(), key=lambda x: x[1], reverse=True
            )
            total = sum(count for _, count in sorted_grade)
            with open(
                os.path.join(
                    output_folder, "all_registrations_computed_grade_bands.csv"
                ),
                "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(["Computed Grade Band", "Count"])
                for grade, count in sorted_grade:
                    writer.writerow([grade, count])
                writer.writerow(["TOTAL", total])

            # 3c. all_registrations_computed_subject_categories.csv
            subject_count = defaultdict(int)
            for row in sorted_data:
                subj = row.get("Computed STEM/Tech/Non-STEM", "").strip()
                subject_count[subj] += 1
            sorted_subject = sorted(
                subject_count.items(), key=lambda x: x[1], reverse=True
            )
            total = sum(count for _, count in sorted_subject)
            with open(
                os.path.join(
                    output_folder, "all_registrations_computed_subject_categories.csv"
                ),
                "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(["Computed STEM/Tech/Non-STEM", "Count"])
                for subj, count in sorted_subject:
                    writer.writerow([subj, count])
                writer.writerow(["TOTAL", total])

            # 4a. US_teachers_by_state.csv
            us_teacher_rows = [
                row
                for row in sorted_data
                if row.get("Country", "").strip() == "United States"
                and row.get("I am a...", "").strip() == "Teacher / Educator"
            ]
            us_teacher_state_count = defaultdict(int)
            for row in us_teacher_rows:
                state = row.get("State", "").strip()
                us_teacher_state_count[state] += 1
            sorted_teacher_state = sorted(
                us_teacher_state_count.items(), key=lambda x: x[1], reverse=True
            )
            total = sum(count for _, count in sorted_teacher_state)
            with open(
                os.path.join(output_folder, "US_teachers_by_state.csv"),
                "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(["State", "Count"])
                for state, count in sorted_teacher_state:
                    writer.writerow([state, count])
                writer.writerow(["TOTAL", total])

            # 4b. US_teachers_computed_grade_bands.csv
            us_teacher_grade_count = defaultdict(int)
            for row in us_teacher_rows:
                grade = row.get("Computed Grade Band", "").strip()
                us_teacher_grade_count[grade] += 1
            sorted_teacher_grade = sorted(
                us_teacher_grade_count.items(), key=lambda x: x[1], reverse=True
            )
            total = sum(count for _, count in sorted_teacher_grade)
            with open(
                os.path.join(output_folder, "US_teachers_computed_grade_bands.csv"),
                "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(["Computed Grade Band", "Count"])
                for grade, count in sorted_teacher_grade:
                    writer.writerow([grade, count])
                writer.writerow(["TOTAL", total])

            # 4c. US_teachers_computed_subject_categories.csv
            us_teacher_subject_count = defaultdict(int)
            for row in us_teacher_rows:
                subj = row.get("Computed STEM/Tech/Non-STEM", "").strip()
                us_teacher_subject_count[subj] += 1
            sorted_teacher_subject = sorted(
                us_teacher_subject_count.items(), key=lambda x: x[1], reverse=True
            )
            total = sum(count for _, count in sorted_teacher_subject)
            with open(
                os.path.join(
                    output_folder, "US_teachers_computed_subject_categories.csv"
                ),
                "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(["Computed STEM/Tech/Non-STEM", "Count"])
                for subj, count in sorted_teacher_subject:
                    writer.writerow([subj, count])
                writer.writerow(["TOTAL", total])

            # 5. all_schools_locations.csv – unique schools with Country, City/Town, and State, sorted ascending by Country.
            schools = {}
            for row in sorted_data:
                school = row.get("School / Company Name", "").strip()
                if school and school not in schools:
                    schools[school] = (
                        row.get("Country", "").strip(),
                        row.get("City/Town", "").strip(),
                        row.get("State", "").strip(),
                    )
            sorted_schools = sorted(schools.items(), key=lambda x: x[1][0].lower())
            with open(
                os.path.join(output_folder, "all_schools_locations.csv"),
                "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["School / Company Name", "Country", "City/Town", "State"]
                )
                for school, info in sorted_schools:
                    writer.writerow([school] + list(info))

            # 6. US_registrations_by_role.csv – For rows with Country "United States", count by "I am a..."
            us_role_count = defaultdict(int)
            for row in sorted_data:
                if row.get("Country", "").strip() == "United States":
                    role = row.get("I am a...", "").strip()
                    us_role_count[role] += 1
            sorted_us_role = sorted(
                us_role_count.items(), key=lambda x: x[1], reverse=True
            )
            total = sum(count for _, count in sorted_us_role)
            with open(
                os.path.join(output_folder, "US_registrations_by_role.csv"),
                "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(["Role", "Count"])
                for role, count in sorted_us_role:
                    writer.writerow([role, count])
                writer.writerow(["TOTAL", total])

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
