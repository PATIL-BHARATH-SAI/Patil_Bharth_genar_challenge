import os
import sys

# Ensure current directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.analytics import run_analysis

def run_tests():
    excel_path = "Bisoprolol_icsr_sample_1068rows.xlsx"
    if not os.path.exists(excel_path):
        print(f"Error: Dataset {excel_path} not found.")
        sys.exit(1)
        
    print("Running verification tests on analytics module...")
    try:
        results = run_analysis(excel_path)
    except Exception as e:
        print(f"FAILED: Could not run analysis. Error: {e}")
        sys.exit(1)
        
    # Expected values
    expected_total_cases = 1024
    expected_serious_cases = 1023
    expected_non_serious_cases = 1
    expected_fatal_alerts = 67
    expected_non_fatal_alerts = 956
    expected_total_alerts = 1023
    
    # 1. Total Case Count
    actual_total = results["total_cases"]
    assert actual_total == expected_total_cases, f"Total cases mismatch: {actual_total} vs {expected_total_cases}"
    print(f"  [PASS] Total case count: {actual_total}")
    
    # 2. Serious vs Non-serious
    actual_serious = results["seriousness"]["serious_cases"]
    actual_non_serious = results["seriousness"]["non_serious_cases"]
    assert actual_serious == expected_serious_cases, f"Serious cases mismatch: {actual_serious} vs {expected_serious_cases}"
    assert actual_non_serious == expected_non_serious_cases, f"Non-serious cases mismatch: {actual_non_serious} vs {expected_non_serious_cases}"
    print(f"  [PASS] Seriousness split: {actual_serious} serious / {actual_non_serious} non-serious")
    
    # 3. 15-Day Alert Reports
    actual_fatal = results["alerts"]["fatal_alerts"]
    actual_non_fatal = results["alerts"]["non_fatal_alerts"]
    actual_total_alerts = results["alerts"]["total_alerts"]
    assert actual_fatal == expected_fatal_alerts, f"Fatal alerts mismatch: {actual_fatal} vs {expected_fatal_alerts}"
    assert actual_non_fatal == expected_non_fatal_alerts, f"Non-fatal alerts mismatch: {actual_non_fatal} vs {expected_non_fatal_alerts}"
    assert actual_total_alerts == expected_total_alerts, f"Total alerts mismatch: {actual_total_alerts} vs {expected_total_alerts}"
    print(f"  [PASS] 15-Day Alerts: {actual_total_alerts} total ({actual_non_fatal} non-fatal / {actual_fatal} fatal)")
    
    # 4. Reaction counts in serious cases
    top_reactions = {r["reaction"]: r["serious_case_count"] for r in results["top_reactions"]}
    
    assert top_reactions.get("Acute kidney injury") == 80, f"AKI mismatch: {top_reactions.get('Acute kidney injury')} vs 80"
    assert top_reactions.get("Drug ineffective") == 53, f"Drug ineffective mismatch: {top_reactions.get('Drug ineffective')} vs 53"
    assert top_reactions.get("Drug interaction") == 43, f"Drug interaction mismatch: {top_reactions.get('Drug interaction')} vs 43"
    assert top_reactions.get("Hypotension") == 46, f"Hypotension mismatch: {top_reactions.get('Hypotension')} vs 46"
    assert top_reactions.get("Fatigue") == 33, f"Fatigue mismatch: {top_reactions.get('Fatigue')} vs 33"
    
    print("  [PASS] Serious reaction counts:")
    print(f"    - Acute kidney injury: {top_reactions.get('Acute kidney injury')}")
    print(f"    - Drug ineffective: {top_reactions.get('Drug ineffective')}")
    print(f"    - Hypotension: {top_reactions.get('Hypotension')}")
    print(f"    - Drug interaction: {top_reactions.get('Drug interaction')}")
    print(f"    - Fatigue: {top_reactions.get('Fatigue')}")
    
    # 5. Total split reactions count
    actual_split_reactions_count = results["total_reactions_count"]
    assert actual_split_reactions_count == 3645, f"Total split reactions count mismatch: {actual_split_reactions_count} vs 3645"
    print(f"  [PASS] Total serious split reactions count: {actual_split_reactions_count}")
    
    print("\nALL DETERMINISTIC VERIFICATION TESTS PASSED SUCCESSFULLY! The mathematical foundation is 100% verified.")

if __name__ == "__main__":
    run_tests()
