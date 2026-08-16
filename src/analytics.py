import os
import pandas as pd
import numpy as np
from datetime import datetime

def clean_date_str(date_val):
    """
    Cleans date values from Excel (which may be float, int, or string)
    and returns a string in YYYY-MM-DD format, or None.
    """
    if pd.isna(date_val):
        return None
    
    # Convert to string and strip float '.0' suffixes if present
    s = str(date_val).strip()
    if s.endswith(".0"):
        s = s[:-2]
        
    if not s:
        return None
    
    # Try parsing YYYYMMDD
    if len(s) == 8 and s.isdigit():
        try:
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        except Exception:
            pass
            
    # Try parsing standard YYYY-MM-DD
    try:
        dt = pd.to_datetime(s)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return s

def calculate_age_in_years(age, unit):
    """
    Converts E2B age units to years.
    800: Decade
    801: Year
    802: Month
    803: Week
    804: Day
    805: Hour
    """
    if pd.isna(age):
        return np.nan
    if pd.isna(unit):
        return age  # default to years if unit is missing
    
    unit_str = str(unit).lower().strip()
    try:
        age_val = float(age)
    except ValueError:
        return np.nan

    if unit_str in ["year", "801", "801.0"]:
        return age_val
    elif unit_str in ["decade", "800", "800.0"]:
        return age_val * 10.0
    elif unit_str in ["month", "802", "802.0"]:
        return age_val / 12.0
    elif unit_str in ["week", "803", "803.0"]:
        return age_val / 52.179
    elif unit_str in ["day", "804", "804.0"]:
        return age_val / 365.25
    elif unit_str in ["hour", "805", "805.0"]:
        return age_val / 8766.0
    else:
        return age_val  # fallback

def get_age_group(age_years, age_group_raw):
    """
    Categorizes the age into standard groups.
    """
    if not pd.isna(age_years):
        if age_years < 18:
            return "Pediatric (<18)"
        elif age_years < 65:
            return "Adult (18-64)"
        else:
            return "Elderly (>=65)"
            
    if not pd.isna(age_group_raw):
        group_str = str(age_group_raw).lower().strip()
        if "elderly" in group_str:
            return "Elderly (>=65)"
        elif "adult" in group_str:
            return "Adult (18-64)"
        elif any(k in group_str for k in ["neonate", "child", "pediatric", "infant", "adolescent"]):
            return "Pediatric (<18)"
            
    return "Unknown"


def classify_report_source(reporttype):
    """
    Maps the source category used in the challenge tabulations.
    """
    if pd.isna(reporttype):
        return "spontaneous"

    reporttype_str = str(reporttype).lower().strip()
    if "study" in reporttype_str:
        return "solicited_study"
    if "solicited" in reporttype_str:
        return "solicited_other"
    return "spontaneous"


def normalize_outcomes(outcome_value):
    """
    Splits multi-value outcome strings into normalized outcome labels.
    """
    if pd.isna(outcome_value):
        return []

    items = [item.strip().lower() for item in str(outcome_value).split(",") if item.strip()]
    normalized = []
    for item in items:
        if item == "fatal":
            normalized.append("fatal")
        elif item == "not recovered/not resolved/ongoing":
            normalized.append("not recovered")
        elif item == "recovering/resolving":
            normalized.append("recovering")
        elif item == "recovered/resolved":
            normalized.append("recovered")
        elif item == "recovered/resolved with sequelae":
            normalized.append("recovered with sequelae")
        else:
            normalized.append("unknown")
    return normalized


def collapse_case_outcome(outcomes):
    """
    Collapses reaction-level outcomes into one case-level outcome using a worst-case priority.
    """
    if not outcomes:
        return "Unknown"

    priority = {
        "fatal": 5,
        "not recovered": 4,
        "recovering": 3,
        "recovered with sequelae": 2,
        "recovered": 1,
        "unknown": 0,
    }
    best = max(outcomes, key=lambda item: priority.get(item, -1))
    labels = {
        "fatal": "Fatal",
        "not recovered": "Not recovered / ongoing",
        "recovering": "Recovering / resolving",
        "recovered with sequelae": "Recovered with sequelae",
        "recovered": "Recovered / resolved",
        "unknown": "Unknown",
    }
    return labels[best]

def run_analysis(excel_path):
    """
    Runs the complete deterministic analysis on the ICSR Excel dataset.
    Returns a dictionary of structured figures.
    """
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Dataset not found at {excel_path}")
        
    df = pd.read_excel(excel_path)
    
    # 1. Clean dates
    df["clean_receivedate"] = df["receivedate"].apply(clean_date_str)
    
    # 2. Extract reporting period range
    valid_dates = df["clean_receivedate"].dropna()
    start_date = valid_dates.min()
    end_date = valid_dates.max()
    
    # 3. Deduplicate by safetyreportid to get case-level data
    df_cases = df.drop_duplicates(subset=["safetyreportid"]).copy()
    total_cases = len(df_cases)
    df_cases["source_category"] = df_cases["reporttype"].apply(classify_report_source)
    
    # 4. Seriousness split
    serious_counts = df_cases["serious"].value_counts()
    serious_cases = int(serious_counts.get("serious", 0))
    non_serious_cases = int(serious_counts.get("not serious", 0))
    
    # 5. Demographics - Sex
    sex_counts = df_cases["patient_patientsex"].value_counts(dropna=False)
    sex_breakdown = {
        "female": int(sex_counts.get("female", 0)),
        "male": int(sex_counts.get("male", 0)),
        "unknown": int(sex_counts.get(np.nan, 0)) + int(sex_counts.get("unknown", 0))
    }
    
    # 6. Demographics - Age Group
    df_cases["age_years"] = df_cases.apply(
        lambda r: calculate_age_in_years(r["patient_patientonsetage"], r["patient_patientonsetageunit"]),
        axis=1
    )
    df_cases["age_group"] = df_cases.apply(
        lambda r: get_age_group(r["age_years"], r["patient_patientagegroup"]),
        axis=1
    )
    age_counts = df_cases["age_group"].value_counts()
    age_breakdown = {
        "pediatric": int(age_counts.get("Pediatric (<18)", 0)),
        "adult": int(age_counts.get("Adult (18-64)", 0)),
        "elderly": int(age_counts.get("Elderly (>=65)", 0)),
        "unknown": int(age_counts.get("Unknown", 0))
    }
    
    # 7. Demographics - Country
    df_cases["country_for_reporting"] = df_cases["occurcountry"].fillna(df_cases["primarysource_reportercountry"])
    country_counts = df_cases["country_for_reporting"].value_counts(dropna=False)
    country_breakdown = {}
    for country, count in country_counts.items():
        c_name = str(country).lower().strip() if not pd.isna(country) else "unknown"
        country_breakdown[c_name] = country_breakdown.get(c_name, 0) + int(count)
        
    # 8. Alert Cases / 15-Day Alerts split (fulfillexpeditecriteria == 'yes')
    # Filter serious cases where expedite criteria is met
    df_alerts = df_cases[
        (df_cases["serious"] == "serious") & 
        (df_cases["fulfillexpeditecriteria"].astype(str).str.lower().str.strip() == "yes")
    ]
    total_alerts = len(df_alerts)
    fatal_alerts = int((df_alerts["seriousnessdeath"].astype(str).str.lower().str.strip() == "yes").sum())
    non_fatal_alerts = total_alerts - fatal_alerts
    
    # 9. Reaction / Adverse Event Analysis
    case_seriousness = {
        row["safetyreportid"]: str(row["serious"]).lower().strip()
        for _, row in df_cases.iterrows()
    }
    case_reactions_all = {}
    case_reactions_serious = {}
    case_reactions_non_serious = {}
    total_split_reactions_all = 0
    total_split_reactions_serious = 0
    total_split_reactions_non_serious = 0

    for _, row in df.iterrows():
        case_id = row["safetyreportid"]
        val = row["patient_reaction_reactionmeddrapt"]
        if pd.isna(val):
            continue
        reactions = [r.strip() for r in str(val).split(",") if r.strip()]
        total_split_reactions_all += len(reactions)
        case_reactions_all.setdefault(case_id, set()).update(reactions)

        if case_seriousness.get(case_id) == "serious":
            total_split_reactions_serious += len(reactions)
            case_reactions_serious.setdefault(case_id, set()).update(reactions)
        else:
            total_split_reactions_non_serious += len(reactions)
            case_reactions_non_serious.setdefault(case_id, set()).update(reactions)

    # Count cases per reaction
    reaction_case_counts_all = {}
    reaction_case_counts_serious = {}
    reaction_case_counts_non_serious = {}
    for case_id, reactions in case_reactions_all.items():
        for r in reactions:
            reaction_case_counts_all[r] = reaction_case_counts_all.get(r, 0) + 1
    for case_id, reactions in case_reactions_serious.items():
        for r in reactions:
            reaction_case_counts_serious[r] = reaction_case_counts_serious.get(r, 0) + 1
    for case_id, reactions in case_reactions_non_serious.items():
        for r in reactions:
            reaction_case_counts_non_serious[r] = reaction_case_counts_non_serious.get(r, 0) + 1

    sorted_reactions_all = sorted(reaction_case_counts_all.items(), key=lambda x: (-x[1], x[0]))
    sorted_reactions_serious = sorted(reaction_case_counts_serious.items(), key=lambda x: (-x[1], x[0]))
    reactions_breakdown_all = [
        {
            "reaction": reaction,
            "total_case_count": total_count,
            "serious_case_count": reaction_case_counts_serious.get(reaction, 0),
            "non_serious_case_count": reaction_case_counts_non_serious.get(reaction, 0),
        }
        for reaction, total_count in sorted_reactions_all
    ]
    
    # 10. Monthly Trend analysis (all cases)
    df_cases["month_period"] = df_cases["clean_receivedate"].apply(
        lambda x: x[:7] if x and len(x) >= 7 else "unknown"
    )
    month_counts = df_cases["month_period"].value_counts().sort_index()
    monthly_trend = {month: int(count) for month, count in month_counts.items() if month != "unknown"}

    # 11. Case-level outcomes and tabulations
    case_outcomes = {}
    for case_id, case_rows in df.groupby("safetyreportid"):
        normalized = []
        for value in case_rows["patient_reaction_reactionoutcome"]:
            normalized.extend(normalize_outcomes(value))
        case_outcomes[case_id] = collapse_case_outcome(normalized)

    outcome_counts = pd.Series(list(case_outcomes.values())).value_counts()
    outcome_breakdown = {
        "fatal": int(outcome_counts.get("Fatal", 0)),
        "not_recovered_ongoing": int(outcome_counts.get("Not recovered / ongoing", 0)),
        "recovering_resolving": int(outcome_counts.get("Recovering / resolving", 0)),
        "recovered_resolved": int(outcome_counts.get("Recovered / resolved", 0)),
        "recovered_with_sequelae": int(outcome_counts.get("Recovered with sequelae", 0)),
        "unknown": int(outcome_counts.get("Unknown", 0)),
    }

    def build_source_tabulation(case_frame):
        source_counts = case_frame["source_category"].value_counts()
        return {
            "solicited_study": int(source_counts.get("solicited_study", 0)),
            "solicited_other": int(source_counts.get("solicited_other", 0)),
            "spontaneous": int(source_counts.get("spontaneous", 0)),
            "total": int(len(case_frame)),
        }

    all_cases_tabulation = {
        "serious_unlabelled": build_source_tabulation(df_cases[df_cases["serious"] == "serious"]),
        "non_serious_unlabelled": build_source_tabulation(df_cases[df_cases["serious"] == "not serious"]),
    }
    alert_tabulation = {
        "serious_unlabelled_non_fatal": build_source_tabulation(
            df_alerts[df_alerts["seriousnessdeath"].astype(str).str.lower().str.strip() != "yes"]
        ),
        "serious_unlabelled_fatal": build_source_tabulation(
            df_alerts[df_alerts["seriousnessdeath"].astype(str).str.lower().str.strip() == "yes"]
        ),
    }

    # 12. Create a structured case index listing for the appendix
    case_listing = []
    # Sort cases by received date then safetyreportid
    df_cases_sorted = df_cases.sort_values(by=["clean_receivedate", "safetyreportid"])
    for idx, row in df_cases_sorted.iterrows():
        case_id = row["safetyreportid"]
        # Reactions for this case
        reactions_str = ""
        # Get all reactions for this case across all rows in raw df
        case_rows = df[df["safetyreportid"] == case_id]
        case_all_reactions = []
        for r_val in case_rows["patient_reaction_reactionmeddrapt"]:
            if not pd.isna(r_val):
                case_all_reactions.extend([r.strip() for r in str(r_val).split(",") if r.strip()])
        unique_case_reactions = sorted(list(set(case_all_reactions)))
        reactions_str = "; ".join(unique_case_reactions)
        
        case_listing.append({
            "case_id": str(case_id),
            "date_received": row["clean_receivedate"],
            "country": str(row["country_for_reporting"]).upper() if not pd.isna(row["country_for_reporting"]) else "UNKNOWN",
            "seriousness": str(row["serious"]).upper(),
            "reactions": reactions_str,
            "outcome": case_outcomes.get(case_id, "Unknown")
        })
        
    return {
        "product_name": "Bisoprolol",
        "pader_number": "PADER-FDA-Y0AHP",
        "reporting_period": {
            "start_date": start_date,
            "end_date": end_date
        },
        "total_cases": total_cases,
        "seriousness": {
            "serious_cases": serious_cases,
            "non_serious_cases": non_serious_cases
        },
        "demographics": {
            "sex": sex_breakdown,
            "age_groups": age_breakdown,
            "countries": country_breakdown
        },
        "alerts": {
            "total_alerts": total_alerts,
            "fatal_alerts": fatal_alerts,
            "non_fatal_alerts": non_fatal_alerts
        },
        "outcomes": outcome_breakdown,
        "top_reactions": [
            {"reaction": r, "serious_case_count": count} for r, count in sorted_reactions_serious
        ],
        "top_reactions_all": reactions_breakdown_all,
        "monthly_trend": monthly_trend,
        "tabulations": {
            "all_cases": all_cases_tabulation,
            "alerts": alert_tabulation,
        },
        "case_listing": case_listing,
        "total_reactions_count": total_split_reactions_serious,
        "total_reactions_count_all": total_split_reactions_all,
        "total_reactions_count_non_serious": total_split_reactions_non_serious
    }

if __name__ == "__main__":
    # Test execution
    excel_path = r"c:\Users\HP\Downloads\ASSESMENT\Bisoprolol_icsr_sample_1068rows.xlsx"
    try:
        results = run_analysis(excel_path)
        print("Analysis completed successfully.")
        print(f"Total Cases: {results['total_cases']}")
        print(f"Serious Cases: {results['seriousness']['serious_cases']}")
        print(f"Non-Serious Cases: {results['seriousness']['non_serious_cases']}")
        print(f"Alerts Split: {results['alerts']['non_fatal_alerts']} / {results['alerts']['fatal_alerts']}")
        print(f"Top 5 Reactions:")
        for r in results['top_reactions'][:5]:
            print(f"  - {r['reaction']}: {r['serious_case_count']}")
    except Exception as e:
        print(f"Error during test run: {e}")
