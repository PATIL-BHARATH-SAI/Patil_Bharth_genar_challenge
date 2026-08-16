import os
import json
from dotenv import load_dotenv

load_dotenv()

genai = None
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    # pyrefly: ignore [missing-import]
    import google.generativeai as genai

    genai.configure(api_key=api_key)


def _format_reporting_period(packet):
    period = packet["reporting_period"]
    return f"{period['start_date']} to {period['end_date']}"


def _offline_generate_section(section_id, evidence_packet):
    """
    Deterministic fallback writer used when no Gemini API key is configured.
    """
    if section_id == "narrative_summary":
        top = evidence_packet["top_reactions_serious_cases"]
        first = ", ".join(
            f"{item['reaction']} ({item['serious_case_count']})" for item in top[:3]
        )
        outcomes = evidence_packet["outcomes"]
        return (
            f"During the reporting period {_format_reporting_period(evidence_packet)}, "
            f"{evidence_packet['total_cases']} unique cases were received for Bisoprolol, "
            f"including {evidence_packet['seriousness']['serious_cases']} serious cases and "
            f"{evidence_packet['seriousness']['non_serious_cases']} non-serious case. "
            f"A total of {evidence_packet['alerts']['total_alerts']} cases met alert criteria, "
            f"including {evidence_packet['alerts']['fatal_alerts']} fatal and "
            f"{evidence_packet['alerts']['non_fatal_alerts']} non-fatal alerts. "
            f"The most frequently reported serious reactions were {first}. "
            f"At the case level, outcomes were most often recorded as recovered/resolved "
            f"({outcomes['recovered_resolved']}) or recovering/resolving "
            f"({outcomes['recovering_resolving']}); {outcomes['fatal']} cases had a fatal outcome."
        )

    if section_id == "case_analysis":
        sex = evidence_packet["demographics"]["sex"]
        age = evidence_packet["demographics"]["age_groups"]
        countries = ", ".join(
            f"{item['country']} ({item['case_count']})"
            for item in evidence_packet["demographics"]["top_countries"]
        )
        outcomes = evidence_packet["outcomes"]
        return (
            f"A total of {evidence_packet['total_cases']} unique cases were identified during "
            f"{_format_reporting_period(evidence_packet)}. "
            f"Serious cases accounted for {evidence_packet['seriousness']['serious_cases']} cases, "
            f"while {evidence_packet['seriousness']['non_serious_cases']} case was non-serious. "
            f"The sex distribution was female {sex['female']}, male {sex['male']}, and unknown {sex['unknown']}. "
            f"Age groups were elderly {age['elderly']}, adult {age['adult']}, pediatric {age['pediatric']}, "
            f"and unknown {age['unknown']}. "
            f"The highest reporting geographies were {countries}. "
            f"Case outcomes were recorded as recovered/resolved in {outcomes['recovered_resolved']} cases, "
            f"recovering/resolving in {outcomes['recovering_resolving']} cases, not recovered/ongoing in "
            f"{outcomes['not_recovered_ongoing']} cases, fatal in {outcomes['fatal']} cases, and unknown in "
            f"{outcomes['unknown']} cases."
        )

    if section_id == "reaction_analysis":
        top_all = ", ".join(
            f"{item['reaction']} ({item['total_case_count']})"
            for item in evidence_packet["top_reactions_all_cases"][:5]
        )
        top_serious = ", ".join(
            f"{item['reaction']} ({item['serious_case_count']})"
            for item in evidence_packet["top_reactions_serious_cases"][:5]
        )
        return (
            f"A total of {evidence_packet['total_reactions_reported_all_cases']} split reaction entries "
            f"were present across all cases, including {evidence_packet['total_reactions_reported_serious_cases']} "
            f"among serious cases and {evidence_packet['total_reactions_reported_non_serious_cases']} among "
            f"non-serious cases. "
            f"The dataset contained {evidence_packet['unique_reactions_count']} unique MedDRA Preferred Terms. "
            f"The most common reactions overall were {top_all}. "
            f"Among serious cases, the most common reactions were {top_serious}. "
            f"No System Organ Class fields were supplied, so analysis is limited to the Preferred Term level."
        )

    if section_id == "serious_cases":
        alert = evidence_packet["tabulation_15_day_alerts"]
        non_fatal = alert["serious_unlabelled_non_fatal"]
        fatal = alert["serious_unlabelled_fatal"]
        return (
            f"During the reporting period, {evidence_packet['total_alerts']} cases met 15-day alert criteria. "
            f"This included {evidence_packet['non_fatal_alerts']} non-fatal alerts and "
            f"{evidence_packet['fatal_alerts']} fatal alerts. "
            f"Non-fatal alerts were distributed as {non_fatal['solicited_study']} solicited study cases, "
            f"{non_fatal['solicited_other']} other solicited cases, and {non_fatal['spontaneous']} spontaneous cases. "
            f"Fatal alerts were distributed as {fatal['solicited_study']} solicited study cases, "
            f"{fatal['solicited_other']} other solicited cases, and {fatal['spontaneous']} spontaneous cases. "
            f"These figures are presented descriptively and do not imply any medical interpretation beyond the reported counts."
        )

    if section_id == "trends":
        metrics = evidence_packet["metrics"]
        return (
            f"Monthly reporting volume averaged {metrics['average_monthly_cases']} cases across the reporting interval. "
            f"The highest monthly volume occurred in {metrics['max_volume_month']['month']} "
            f"({metrics['max_volume_month']['case_count']} cases), while the lowest occurred in "
            f"{metrics['min_volume_month']['month']} ({metrics['min_volume_month']['case_count']} cases). "
            f"These variations describe reporting volume only; they should not be interpreted as a confirmed safety signal without additional review."
        )

    if section_id == "history_actions":
        return evidence_packet["message"]

    return json.dumps(evidence_packet, indent=2)

def call_llm(prompt_text, model_name="gemini-3.5-flash"):
    """
    Calls the Gemini API with the given prompt.
    """
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError(
            "GEMINI_API_KEY is not set in the environment. "
            "Please create a .env file containing: GEMINI_API_KEY=your_key"
        )
    
    # Set up configuration parameters
    generation_config = {
        "temperature": 0.0,  # Zero temperature to maximize determinism and compliance
    }
    
    model = genai.GenerativeModel(model_name, generation_config=generation_config)
    response = model.generate_content(prompt_text)
    return response.text.strip()

def generate_section(section_id, evidence_packet, prompt_dir="prompts", model_name="gemini-3.5-flash"):
    """
    Loads the prompt template for a section, formats it with the evidence packet,
    and calls the LLM to write the prose.
    """
    prompt_path = os.path.join(prompt_dir, f"{section_id}.txt")
    if not os.path.exists(prompt_path):
        # Fallback prompt in case the file doesn't exist
        prompt_template = (
            "Role: Regulatory writer.\n"
            "Evidence Packet:\n{{ EVIDENCE_PACKET }}\n"
            "Instructions: Summarize only the facts in the evidence packet in a regulatory tone."
        )
    else:
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
            
    # Serialize the packet to formatted JSON
    packet_json_str = json.dumps(evidence_packet, indent=2)
    
    # Simple replacement of placeholders
    prompt_text = prompt_template.replace("{{ EVIDENCE_PACKET }}", packet_json_str)
    
    if not os.getenv("GEMINI_API_KEY"):
        return _offline_generate_section(section_id, evidence_packet)

    return call_llm(prompt_text, model_name=model_name)
