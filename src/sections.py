def build_reporting_period_packet(results):
    """
    Extracts data for Section 1: Reporting Period.
    """
    return {
        "product_name": results["product_name"],
        "pader_number": results["pader_number"],
        "start_date": results["reporting_period"]["start_date"],
        "end_date": results["reporting_period"]["end_date"],
        "report_type": "Annual PADER"
    }

def build_narrative_summary_packet(results):
    """
    Extracts data for Section 2: Narrative Summary and Analysis.
    """
    return {
        "reporting_period": results["reporting_period"],
        "total_cases": results["total_cases"],
        "seriousness": results["seriousness"],
        "alerts": results["alerts"],
        "outcomes": results["outcomes"],
        "top_reactions_all_cases": [
            {
                "reaction": r["reaction"],
                "total_case_count": r["total_case_count"],
                "serious_case_count": r["serious_case_count"],
            }
            for r in results["top_reactions_all"][:5]
        ],
        "top_reactions_serious_cases": results["top_reactions"][:5],
    }

def build_case_analysis_packet(results):
    """
    Extracts data for Section 3: Summary Analysis of Cases.
    """
    # Get top 5 countries by case volume
    sorted_countries = sorted(results["demographics"]["countries"].items(), key=lambda x: x[1], reverse=True)
    top_countries = [{"country": country.upper(), "case_count": count} for country, count in sorted_countries[:5]]
    
    return {
        "reporting_period": results["reporting_period"],
        "total_cases": results["total_cases"],
        "seriousness": results["seriousness"],
        "demographics": {
            "sex": results["demographics"]["sex"],
            "age_groups": results["demographics"]["age_groups"],
            "top_countries": top_countries
        },
        "outcomes": results["outcomes"],
    }

def build_reaction_analysis_packet(results):
    """
    Extracts data for Section 4: Reaction / Adverse Event Analysis.
    """
    # Return top 10 reactions and total reaction count
    return {
        "total_reactions_reported_all_cases": results["total_reactions_count_all"],
        "total_reactions_reported_serious_cases": results["total_reactions_count"],
        "total_reactions_reported_non_serious_cases": results["total_reactions_count_non_serious"],
        "unique_reactions_count": len(results["top_reactions_all"]),
        "top_reactions_all_cases": results["top_reactions_all"][:10],
        "top_reactions_serious_cases": results["top_reactions"][:10],
    }

def build_serious_cases_packet(results):
    """
    Extracts data for Section 5: Serious Cases / 15-Day Alerts.
    """
    return {
        "total_alerts": results["alerts"]["total_alerts"],
        "fatal_alerts": results["alerts"]["fatal_alerts"],
        "non_fatal_alerts": results["alerts"]["non_fatal_alerts"],
        "tabulation_15_day_alerts": results["tabulations"]["alerts"],
        "tabulation_all_cases": results["tabulations"]["all_cases"],
    }

def build_trends_packet(results):
    """
    Extracts data for Section 6: Trends and Important Observations.
    """
    # Sort trend by date
    sorted_trend = sorted(results["monthly_trend"].items())
    trend_list = [{"month": month, "case_count": count} for month, count in sorted_trend]
    
    # Calculate simple stats
    counts = [item["case_count"] for item in trend_list]
    max_month = max(trend_list, key=lambda x: x["case_count"]) if trend_list else None
    min_month = min(trend_list, key=lambda x: x["case_count"]) if trend_list else None
    
    return {
        "monthly_trend": trend_list,
        "metrics": {
            "average_monthly_cases": round(sum(counts) / len(counts), 2) if counts else 0,
            "max_volume_month": max_month,
            "min_volume_month": min_month
        }
    }

def build_history_actions_packet(results):
    """
    Extracts data for Section 7: History of Actions.
    Per guide, we explicitly note no information was provided.
    """
    return {
        "actions_provided": False,
        "message": "No history of safety-related actions (such as labeling changes or studies initiated) was supplied for this reporting interval."
    }

def build_all_packets(results):
    """
    Builds and returns evidence packets for all sections.
    """
    return {
        "reporting_period": build_reporting_period_packet(results),
        "narrative_summary": build_narrative_summary_packet(results),
        "case_analysis": build_case_analysis_packet(results),
        "reaction_analysis": build_reaction_analysis_packet(results),
        "serious_cases": build_serious_cases_packet(results),
        "trends": build_trends_packet(results),
        "history_actions": build_history_actions_packet(results)
    }
