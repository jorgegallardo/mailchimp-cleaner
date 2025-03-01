# mailchimp cleaner

a Python script that processes CSV files containing timestamp data, sorts them chronologically, and splits them into separate files based on date ranges

## features

- sorts CSV data by column CD (OPTIN_TIME)
- creates separate CSV files in an `outputs` directory for different date ranges:
  - complete sorted dataset
  - pre-October 15, 2024
  - October 15-31, 2024
  - each subsequent month's data

## usage

1. place your input CSV file in the project root as `raw.csv`
2. ensure the CSV has a datetime column named `OPTIN_TIME` in the format `YYYY-MM-DD HH:MM:SS`
3. run main.py

## version

- 0.1.0 - initial release with basic sorting and date-based file splitting functionality
- 0.1.1 - clear out columns K-BI for students and parents
- 0.1.2 - replace "United States of America" with "United States"
- 0.1.3 - US states and other mappings, clear out country for oxymoron: "United States" listed as "Other - Non-US"
- 0.1.4 - identify @qq.com users as being from China and a non-US state
- 0.1.5 - added country mappings
- 0.1.6 - clean and identify US states with missing country (US only)
- 0.1.7 - identify some "Other - Non-US" states (when City/Town and State match), clear state if non-US country
- 0.1.8 - clean cities, school names
- 0.2.0 - compute grade bands (PK, K-2, 3-5, 6-8, 9-12) and subject areas (STEM, Tech, non-STEM), delete unwanted columns, rearrange columns
- 0.2.1 - non-teacher cleaning, added some city to country mappings, bug fixes
- 0.3.0 - analyze data and create all/US analysis files
- 0.3.1 - bug fix - add country to more known cities
