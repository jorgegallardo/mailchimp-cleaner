import os
import csv
from collections import defaultdict


def registrations_by_country(sorted_data, output_folder):
    country_count = defaultdict(int)
    for row in sorted_data:
        country = row.get("Country", "").strip()
        country_count[country] += 1
    sorted_country = sorted(country_count.items(), key=lambda x: x[1], reverse=True)
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


def us_registrations_by_state(sorted_data, output_folder):
    us_state_count = defaultdict(int)
    for row in sorted_data:
        if row.get("Country", "").strip() == "United States":
            state = row.get("State", "").strip()
            us_state_count[state] += 1
    sorted_us_state = sorted(us_state_count.items(), key=lambda x: x[1], reverse=True)
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


def registrations_by_role(sorted_data, output_folder):
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


def registrations_computed_grade_bands(sorted_data, output_folder):
    grade_band_count = defaultdict(int)
    for row in sorted_data:
        grade = row.get("Computed Grade Band", "").strip()
        grade_band_count[grade] += 1
    sorted_grade = sorted(grade_band_count.items(), key=lambda x: x[1], reverse=True)
    total = sum(count for _, count in sorted_grade)
    with open(
        os.path.join(output_folder, "all_registrations_computed_grade_bands.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["Computed Grade Band", "Count"])
        for grade, count in sorted_grade:
            writer.writerow([grade, count])
        writer.writerow(["TOTAL", total])


def registrations_computed_subject_categories(sorted_data, output_folder):
    subject_count = defaultdict(int)
    for row in sorted_data:
        subj = row.get("Computed STEM/Tech/Non-STEM", "").strip()
        subject_count[subj] += 1
    sorted_subject = sorted(subject_count.items(), key=lambda x: x[1], reverse=True)
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


def us_teachers_by_state(sorted_data, output_folder):
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


def us_teachers_computed_grade_bands(sorted_data, output_folder):
    us_teacher_rows = [
        row
        for row in sorted_data
        if row.get("Country", "").strip() == "United States"
        and row.get("I am a...", "").strip() == "Teacher / Educator"
    ]
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


def us_teachers_computed_subject_categories(sorted_data, output_folder):
    us_teacher_rows = [
        row
        for row in sorted_data
        if row.get("Country", "").strip() == "United States"
        and row.get("I am a...", "").strip() == "Teacher / Educator"
    ]
    us_teacher_subject_count = defaultdict(int)
    for row in us_teacher_rows:
        subj = row.get("Computed STEM/Tech/Non-STEM", "").strip()
        us_teacher_subject_count[subj] += 1
    sorted_teacher_subject = sorted(
        us_teacher_subject_count.items(), key=lambda x: x[1], reverse=True
    )
    total = sum(count for _, count in sorted_teacher_subject)
    with open(
        os.path.join(output_folder, "US_teachers_computed_subject_categories.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["Computed STEM/Tech/Non-STEM", "Count"])
        for subj, count in sorted_teacher_subject:
            writer.writerow([subj, count])
        writer.writerow(["TOTAL", total])


def all_schools_locations(sorted_data, output_folder):
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
        writer.writerow(["School / Company Name", "Country", "City/Town", "State"])
        for school, info in sorted_schools:
            writer.writerow([school] + list(info))


def us_registrations_by_role(sorted_data, output_folder):
    us_role_count = defaultdict(int)
    for row in sorted_data:
        if row.get("Country", "").strip() == "United States":
            role = row.get("I am a...", "").strip()
            us_role_count[role] += 1
    sorted_us_role = sorted(us_role_count.items(), key=lambda x: x[1], reverse=True)
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


def referral_source_analysis(sorted_data, output_folder):
    REFERRAL_SOURCE_CATEGORIES = [
        "Social Media (e.g., LinkedIn, X, Instagram)",
        "Email",
        "Internet Search (e.g., Google, Bing)",
        "Word of Mouth (e.g., a friend or colleague)",
    ]
    referral_source_count = {cat: 0 for cat in REFERRAL_SOURCE_CATEGORIES}
    referral_source_count["(Blank)"] = 0
    for row in sorted_data:
        val = row.get("Referral Source", "")
        val_stripped = val.strip() if val else ""
        if val_stripped in REFERRAL_SOURCE_CATEGORIES:
            referral_source_count[val_stripped] += 1
        elif val_stripped == "":
            referral_source_count["(Blank)"] += 1
    with open(
        os.path.join(output_folder, "referral_source_analysis.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["Referral Source Category", "Count"])
        for cat in REFERRAL_SOURCE_CATEGORIES + ["(Blank)"]:
            writer.writerow([cat, referral_source_count[cat]])
        writer.writerow(["TOTAL", sum(referral_source_count.values())])


def run_all_analyses(sorted_data, output_folder):
    registrations_by_country(sorted_data, output_folder)
    us_registrations_by_state(sorted_data, output_folder)
    registrations_by_role(sorted_data, output_folder)
    registrations_computed_grade_bands(sorted_data, output_folder)
    registrations_computed_subject_categories(sorted_data, output_folder)
    us_teachers_by_state(sorted_data, output_folder)
    us_teachers_computed_grade_bands(sorted_data, output_folder)
    us_teachers_computed_subject_categories(sorted_data, output_folder)
    all_schools_locations(sorted_data, output_folder)
    us_registrations_by_role(sorted_data, output_folder)
    referral_source_analysis(sorted_data, output_folder)
