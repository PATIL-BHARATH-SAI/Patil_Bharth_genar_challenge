import os
import sys
from dotenv import load_dotenv
from src.graph import build_workflow

def main():
    load_dotenv()

    has_api_key = bool(os.getenv("GEMINI_API_KEY"))

    # Find dataset path
    excel_path = "Bisoprolol_icsr_sample_1068rows.xlsx"
    if not os.path.exists(excel_path):
        # Check current directory
        excel_path = os.path.join(os.path.dirname(__file__), "Bisoprolol_icsr_sample_1068rows.xlsx")
        
    if not os.path.exists(excel_path):
        print(f"ERROR: Dataset file '{excel_path}' not found.")
        sys.exit(1)
    
    print(f"Starting PADER Report Generation Pipeline...")
    print(f"Dataset path: {excel_path}")
    if has_api_key:
        print("Writer mode: Gemini API enabled.")
    else:
        print("Writer mode: Offline deterministic fallback enabled (no GEMINI_API_KEY found).")
    
    # Build the compiled workflow
    app = build_workflow()
    
    # Initialize state
    initial_state = {
        "excel_path": excel_path,
        "results": {},
        "packets": {},
        "sections": {},
        "status": {},
        "feedback": {},
        "output_path": ""
    }
    
    try:
        # Run the workflow graph
        final_state = app.invoke(initial_state)
        print("\n" + "="*80)
        print("SUCCESS: Periodic Adverse Drug Experience Report (PADER) generation complete!")
        print(f"Output Report Path: {final_state['output_path']}")
        print("="*80 + "\n")
    except Exception as e:
        print(f"\nERROR running pipeline: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
