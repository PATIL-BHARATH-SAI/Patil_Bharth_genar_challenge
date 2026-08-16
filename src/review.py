import os

def review_section(section_id, title, content):
    """
    Presents a generated section to the human reviewer in the console.
    Supports an automated bypass if AUTO_APPROVE=1 is set.
    Returns: (status, feedback)
      status: "approved" or "flagged"
      feedback: manual text feedback if flagged, else None
    """
    # Check if auto-approve mode is enabled
    if os.getenv("AUTO_APPROVE") == "1":
        print(f"--> Section '{title}' AUTO-APPROVED (Non-interactive Mode).")
        return "approved", None
        
    print("\n" + "="*80)
    print(f" HUMAN REVIEW REQUIRED FOR SECTION: {title}")
    print("="*80)
    print(content)
    print("="*80)
    
    while True:
        choice = input("\nAction: [A]pprove (Keep) or [F]lag for changes? ").strip().lower()
        if choice in ["a", "approve", "k", "keep", "y", "yes"]:
            print(f"--> Section '{title}' APPROVED.")
            return "approved", None
        elif choice in ["f", "flag", "r", "reject", "n", "no"]:
            feedback = input("Provide feedback or instructions for regeneration: ").strip()
            print(f"--> Section '{title}' FLAGGED.")
            return "flagged", feedback
        else:
            print("Invalid input. Please enter 'A' to approve or 'F' to flag.")
