import csv
from datetime import datetime, timedelta
import os
from collections import defaultdict


def process_csv(input_file, output_folder, sort_column):
    """
    Processes a CSV file by:
      - Reading and parsing the data.
      - Sorting the data based on the sort_column.
      - Cleaning rows where column D is "Student" or "Parent" by clearing values
        between columns "Number of Students" and the second occurrence of
        "Other (please specify in Notes)".
      - Writing the full sorted-and-cleaned data to a CSV file.
      - Splitting and writing data into separate files based on date ranges.
    """
    try:
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

            # Sort the data based on the datetime in sort_column
            sorted_data = sorted(data, key=lambda row: row[sort_column])

            # --- Cleaning Step: Remove values in a range of columns if column D is "Student" or "Parent" ---
            # Ensure there are at least 4 columns so that column D exists.
            if len(fieldnames) < 4:
                raise ValueError(
                    "CSV does not contain enough columns to check column D."
                )

            # Column D (0-indexed position 3)
            col_d_header = fieldnames[3]

            # Find the index for the "Number of Students" column (assumed column K)
            try:
                start_index = fieldnames.index("Number of Students")
            except ValueError:
                raise ValueError("Header 'Number of Students' not found.")

            # Find all occurrences of "Other (please specify in Notes)" in the headers
            other_indices = [
                i
                for i, header in enumerate(fieldnames)
                if header == "Other (please specify in Notes)"
            ]
            if len(other_indices) < 2:
                raise ValueError(
                    "Expected at least 2 occurrences of 'Other (please specify in Notes)', but found fewer."
                )
            # Use the second occurrence as the end index
            end_index = other_indices[1]

            # For each row, if the value in column D is "Student" or "Parent",
            # clear out every column from "Number of Students" to the second "Other (please specify in Notes)" (inclusive).
            for row in sorted_data:
                if row[col_d_header].strip() in ["Student", "Parent"]:
                    for col in fieldnames[start_index : end_index + 1]:
                        row[col] = ""

            # Create mapping of date ranges
            date_ranges = defaultdict(list)
            for row in sorted_data:
                date = row[sort_column]
                if date < datetime(2024, 10, 15):
                    date_ranges["1-pre1015.csv"].append(row)
                elif datetime(2024, 10, 15) <= date < datetime(2024, 11, 1):
                    date_ranges["2-1031.csv"].append(row)
                else:
                    # Format key as 'YYYY-MM' for sorting
                    key = f"{date.year}-{date.month:02d}"
                    date_ranges[key].append(row)

            # Write the full sorted and cleaned data to a file named "0-sorted-and-cleaned.csv"
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
                    # When writing, convert the datetime back to string
                    row_to_write = row.copy()
                    row_to_write[sort_column] = row_to_write[sort_column].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    writer.writerow(row_to_write)

            # Process special files first
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

            # Process monthly files starting with index 3
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
