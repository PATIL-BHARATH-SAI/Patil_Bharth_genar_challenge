import os
import csv

def generate_reaction_table(results):
    """
    Generates a Markdown table of the top adverse reactions.
    Since no SOC was supplied, we explicitly state this and report at the PT level.
    """
    markdown = "\n### MedDRA Preferred Term (PT) Case Counts (Top 20)\n\n"
    markdown += "> [!NOTE]\n"
    markdown += "> The dataset does not contain System Organ Class (SOC) fields. "
    markdown += "Adverse events are reported directly at the Preferred Term (PT) level in accordance with PADER guidance.\n\n"
    
    markdown += "| Preferred Term (PT) | Serious Cases | Non-Serious Cases | Total |\n"
    markdown += "| :--- | :---: | :---: | :---: |\n"

    for item in results["top_reactions_all"][:20]:
        pt = item["reaction"]
        serious_count = item["serious_case_count"]
        non_serious_count = item["non_serious_case_count"]
        total_count = item["total_case_count"]
        markdown += f"| {pt} | {serious_count} | {non_serious_count} | {total_count} |\n"
        
    return markdown

def generate_15_day_alerts_table(results):
    """
    Generates the Summary of 15-Day Alert Reports table.
    """
    alert_rows = results["tabulations"]["alerts"]
    non_fatal = alert_rows["serious_unlabelled_non_fatal"]
    fatal = alert_rows["serious_unlabelled_fatal"]
    markdown = "\n### Summary Tabulation of 15-Day Alert Reports\n\n"
    markdown += "| Category | Solicited (Study) | Solicited (Other) | Spontaneous | Total |\n"
    markdown += "| :--- | :---: | :---: | :---: | :---: |\n"
    markdown += (
        f"| **Serious, Unlabelled — Non-Fatal** | {non_fatal['solicited_study']} | "
        f"{non_fatal['solicited_other']} | {non_fatal['spontaneous']} | {non_fatal['total']} |\n"
    )
    markdown += (
        f"| **Serious, Unlabelled — Fatal** | {fatal['solicited_study']} | "
        f"{fatal['solicited_other']} | {fatal['spontaneous']} | {fatal['total']} |\n"
    )
    markdown += (
        f"| **Total** | **{non_fatal['solicited_study'] + fatal['solicited_study']}** | "
        f"**{non_fatal['solicited_other'] + fatal['solicited_other']}** | "
        f"**{non_fatal['spontaneous'] + fatal['spontaneous']}** | "
        f"**{non_fatal['total'] + fatal['total']}** |\n"
    )
    return markdown

def generate_all_cases_table(results):
    """
    Generates the Summary of All ICSR Cases table.
    """
    serious = results["tabulations"]["all_cases"]["serious_unlabelled"]
    non_serious = results["tabulations"]["all_cases"]["non_serious_unlabelled"]
    
    markdown = "\n### Summary Tabulation of All ICSR Cases\n\n"
    markdown += "| Category | Solicited (Study) | Solicited (Other) | Spontaneous | Total |\n"
    markdown += "| :--- | :---: | :---: | :---: | :---: |\n"
    markdown += (
        f"| **Serious, Unlabelled** | {serious['solicited_study']} | {serious['solicited_other']} | "
        f"{serious['spontaneous']} | {serious['total']} |\n"
    )
    markdown += (
        f"| **Non-Serious, Unlabelled** | {non_serious['solicited_study']} | "
        f"{non_serious['solicited_other']} | {non_serious['spontaneous']} | {non_serious['total']} |\n"
    )
    markdown += (
        f"| **Total Cases** | **{serious['solicited_study'] + non_serious['solicited_study']}** | "
        f"**{serious['solicited_other'] + non_serious['solicited_other']}** | "
        f"**{serious['spontaneous'] + non_serious['spontaneous']}** | "
        f"**{serious['total'] + non_serious['total']}** |\n"
    )
    return markdown

def generate_case_listing_table(results):
    """
    Generates the Case Index / Listing table.
    """
    markdown = "\n### Case Index / Listing (Top 50)\n\n"
    markdown += "> [!NOTE]\n"
    markdown += "> Showing the first 50 cases ordered by Date Received. The full case listing is provided in `output/case_index.csv`.\n\n"
    markdown += "| Case ID | Date Received | Country | Seriousness | Preferred Term(s) | Outcome |\n"
    markdown += "| :--- | :--- | :---: | :---: | :--- | :---: |\n"
    
    for case in results["case_listing"][:50]:
        markdown += f"| {case['case_id']} | {case['date_received']} | {case['country']} | {case['seriousness']} | {case['reactions']} | {case['outcome']} |\n"
        
    return markdown


def write_case_listing_csv(results, output_path="output/case_index.csv"):
    """
    Writes the full case listing to CSV for reviewer traceability.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["case_id", "date_received", "country", "seriousness", "reactions", "outcome"],
        )
        writer.writeheader()
        writer.writerows(results["case_listing"])

def assemble_report(results, sections, output_path="output/report.md"):
    """
    Assembles the final PADER report markdown file.
    """
    start_date = results["reporting_period"]["start_date"]
    end_date = results["reporting_period"]["end_date"]
    
    report_content = f"""# Periodic Adverse Drug Experience Report (PADER)

**Product:** {results['product_name'].upper()}  
**Application Number:** B-1  
**Marketing Authorization Holder:** Dev Pharma Client  
**Reporting Period:** {start_date} to {end_date}  
**PADER Number:** {results['pader_number']}  
**Date of Report:** {datetime_now()}  

---

## 1. Reporting Period
This report covers the one-year reporting period from **{start_date}** to **{end_date}**. The reporting period and data cut-off date were established based on the received dates present in the source safety dataset.

---

## 2. Narrative Summary and Analysis
{sections.get('narrative_summary', 'Pending draft.')}

---

## 3. Summary Analysis of Cases
{sections.get('case_analysis', 'Pending draft.')}

{generate_all_cases_table(results)}

---

## 4. Reaction / Adverse Event Analysis
{sections.get('reaction_analysis', 'Pending draft.')}

{generate_reaction_table(results)}

---

## 5. Serious Cases / 15-Day Alerts
{sections.get('serious_cases', 'Pending draft.')}

{generate_15_day_alerts_table(results)}

---

## 6. Trends and Important Observations
{sections.get('trends', 'Pending draft.')}

---

## 7. History of Actions
{sections.get('history_actions', 'Pending draft.')}

---

## 8. Case Index / Listing
{generate_case_listing_table(results)}
"""
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    write_case_listing_csv(results)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content.strip() + "\n")
        
    print(f"--> PADER Report assembled successfully at: {output_path}")
    return output_path

def datetime_now():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")
