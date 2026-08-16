from typing import Dict, TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from src.analytics import run_analysis
from src.sections import build_all_packets
from src.llm_writer import generate_section
from src.review import review_section
from src.assemble import assemble_report

class ReportState(TypedDict):
    excel_path: str
    results: Dict
    packets: Dict
    sections: Dict
    status: Dict       # section_id -> "pending", "approved", "flagged"
    feedback: Dict     # section_id -> manual feedback string
    output_path: str

# 1. Analytics Node
def run_analytics_node(state: ReportState) -> Dict:
    print("\n--> [Node: Run Analytics] Processing safety data...")
    results = run_analysis(state["excel_path"])
    return {"results": results}

# 2. Packets Node
def build_packets_node(state: ReportState) -> Dict:
    print("\n--> [Node: Build Packets] Extracting section-specific evidence packets...")
    packets = build_all_packets(state["results"])
    # Initialize status for each report section
    initial_status = {}
    initial_sections = {}
    initial_feedback = {}
    
    sections_list = ["narrative_summary", "case_analysis", "reaction_analysis", "serious_cases", "trends", "history_actions"]
    for sec in sections_list:
        initial_status[sec] = "pending"
        initial_sections[sec] = ""
        initial_feedback[sec] = ""
        
    return {
        "packets": packets, 
        "status": initial_status, 
        "sections": initial_sections,
        "feedback": initial_feedback
    }

# 3. LLM Writer Node
def run_writer_node(state: ReportState) -> Dict:
    print("\n--> [Node: LLM Writer] Generating drafts for pending or flagged sections...")
    current_sections = state["sections"].copy()
    current_status = state["status"].copy()
    
    for sec_id, status in current_status.items():
        if status in ["pending", "flagged"]:
            print(f"  Drafting/Regenerating section: {sec_id}...")
            evidence_packet = state["packets"][sec_id]
            
            # Incorporate user feedback if it was flagged
            if status == "flagged" and state["feedback"].get(sec_id):
                feedback = state["feedback"][sec_id]
                # We can append feedback instructions dynamically to the prompt
                evidence_packet = evidence_packet.copy()
                evidence_packet["_reviewer_feedback"] = feedback
            
            draft = generate_section(sec_id, evidence_packet)
            current_sections[sec_id] = draft
            current_status[sec_id] = "drafted"
            
    return {"sections": current_sections, "status": current_status}

# 4. Human Review Node
def run_review_node(state: ReportState) -> Dict:
    print("\n--> [Node: Human Review] Blocking for reviewer input...")
    current_status = state["status"].copy()
    current_feedback = state["feedback"].copy()
    
    titles = {
        "narrative_summary": "2. Narrative Summary and Analysis",
        "case_analysis": "3. Summary Analysis of Cases",
        "reaction_analysis": "4. Reaction / Adverse Event Analysis",
        "serious_cases": "5. Serious Cases / 15-Day Alerts",
        "trends": "6. Trends and Important Observations",
        "history_actions": "7. History of Actions"
    }
    
    for sec_id in current_status.keys():
        # Review if not already approved
        if current_status[sec_id] != "approved":
            status, feedback = review_section(sec_id, titles[sec_id], state["sections"][sec_id])
            current_status[sec_id] = status
            if status == "flagged":
                current_feedback[sec_id] = feedback
            else:
                current_feedback[sec_id] = ""
                
    return {"status": current_status, "feedback": current_feedback}

# 5. Assemble Node
def run_assemble_node(state: ReportState) -> Dict:
    print("\n--> [Node: Assemble Report] Merging all sections and generating report.md...")
    output_path = assemble_report(state["results"], state["sections"])
    return {"output_path": output_path}

# Define conditional transition logic
def should_continue(state: ReportState):
    for sec_id, status in state["status"].items():
        if status == "flagged":
            print(f"\n[Flow Control] Section '{sec_id}' was flagged. Routing back to Writer Node for regeneration...")
            return "writer"
    print("\n[Flow Control] All sections approved. Routing to Assemble Node...")
    return "assemble"

def build_workflow() -> StateGraph:
    workflow = StateGraph(ReportState)
    
    # Add nodes
    workflow.add_node("analytics", run_analytics_node)
    workflow.add_node("packets", build_packets_node)
    workflow.add_node("writer", run_writer_node)
    workflow.add_node("review", run_review_node)
    workflow.add_node("assemble", run_assemble_node)
    
    # Set entry point
    workflow.set_entry_point("analytics")
    
    # Add transitions
    workflow.add_edge("analytics", "packets")
    workflow.add_edge("packets", "writer")
    workflow.add_edge("writer", "review")
    
    # Conditional loop for human feedback
    workflow.add_conditional_edges(
        "review",
        should_continue,
        {
            "writer": "writer",
            "assemble": "assemble"
        }
    )
    
    workflow.add_edge("assemble", END)
    
    return workflow.compile()
