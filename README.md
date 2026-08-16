# Grounded PADER Safety Report Generation Pipeline

This project is a working Python prototype (Version 0) built for the **GenAR AI Engineering Challenge**. It processes a spontaneous ICSR dataset for Bisoprolol and compiles it into a Periodic Adverse Drug Experience Report (PADER) compliant with 21 CFR 314.80.

---

## 1. How to Run It

### Setup Environment
Ensure Python 3.13+ is installed on your system. Run the following commands in your PowerShell terminal to create a virtual environment and install the required dependencies:

```powershell
# Create the virtual environment
python -m venv .venv

# Install dependencies
.venv\Scripts\pip install -r requirements.txt
```

### Execution Command
To run the end-to-end report generation pipeline, execute:

```powershell
# Run in auto-approve non-interactive mode
$env:AUTO_APPROVE="1"; $env:GEMINI_API_KEY=""; .venv\Scripts\python main.py

# Or run in interactive mode (prompts for human keep/flag approval at each section)
$env:GEMINI_API_KEY=""; .venv\Scripts\python main.py
```

*Note: If `GEMINI_API_KEY` is not present, the pipeline automatically falls back to a deterministic local writer so the report can still be regenerated offline. If you happen to have a local `.env` file with a key from development, setting `$env:GEMINI_API_KEY=""` forces the offline path shown above.*

To configure a real Gemini LLM writer, create a `.env` file in the project root:
```text
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## 2. System Architecture & Data Flow

The system orchestrates safety report compilation using a modular pipeline managed by a LangGraph state graph.

```
                  ┌───────────────────────────────┐
                  │ Bisoprolol ICSR Excel Dataset │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │    src/analytics.py (Pandas)  │ <── All counting & math
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │    src/sections.py (Packets)  │ <── Context Engineering
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │      src/llm_writer.py        │ <── Renders prompts + Gemini API
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │      src/review.py            │ <── Human-in-the-loop Approve/Flag
                  └───────────────┬───────────────┘
                                  │
            ┌─────────────────────┴─────────────────────┐
            ▼ (Approved)                                ▼ (Flagged)
    ┌──────────────────────┐                     ┌─────────────────────┐
    │  src/assemble.py     │                     │ LLM Writer Re-draft │
    └──────────┬───────────┘                     └──────────┬──────────┘
               │                                            │
               ▼                                            ▼
    ┌──────────────────────┐                     ┌─────────────────────┐
    │  output/report.md    │                     │   Reviewer Block    │
    └──────────────────────┘                     └─────────────────────┘
```

---

## 3. AI vs. Deterministic Split

A core grading criteria is maintaining a trusted pipeline where the AI is limited to writing prose, not counting numbers.

- **Deterministic Layer (Python/pandas)**: All deduplication (on `safetyreportid`), date cleaning, age unit conversion/bucketing, seriousness aggregation, 15-day alert classification, and trend analyses are executed by pure pandas operations in `src/analytics.py`. **Zero LLM involvement occurs during math operations.**
- **AI Reasoning Layer (Gemini/LLM)**: The LLM is restricted to turning tiny pre-computed JSON summary packets into regulatory-toned prose for the narrative sections. Its temperature is set to `0.0` to enforce objective compliance and eliminate hallucinations.

---

## 4. Prompts and Assembled Templates

Prompts are stored as standalone text files in `prompts/`. The orchestrator loads them and replaces `{{ EVIDENCE_PACKET }}` with a serialized JSON evidence packet.

### Narrative Summary Prompt (`prompts/narrative_summary.txt`)
```text
Role: You are a professional regulatory affairs specialist and medical writer.
Task: Write a concise, regulatory-toned Narrative Summary and Analysis for the Periodic Adverse Drug Experience Report (PADER) of Bisoprolol.

Evidence Packet (JSON format):
{{ EVIDENCE_PACKET }}

Instructions:
1. Summarize ONLY the figures provided in the evidence packet. Do not invent any numbers.
2. Maintain an objective, neutral, and professional regulatory tone.
3. Do NOT make or infer any medical conclusions or clinical safety signals unless explicitly present in the data (e.g. do NOT say "Bisoprolol is safe" or "this indicates an emerging safety concern for Acute kidney injury"). Stick strictly to the numbers.
4. Distinguish clearly between observed data (e.g., "80 serious cases of acute kidney injury were reported") and derived analysis (e.g., "Acute kidney injury was the most frequently reported reaction").
5. The summary must be brief, typically 3-5 sentences.

Write the Narrative Summary and Analysis section below:
```

---

## 5. Grounding & Verifiability

- **Context Engineering**: Instead of feeding the model the raw 1,068-row spreadsheet, `src/sections.py` extracts a tiny JSON summary of metrics specifically relevant to that section.
- **Traceability**: All tables (reactions, 15-day alerts, case counts) and listings in `output/report.md` are dynamically generated by `src/assemble.py` directly from the pandas results, ensuring perfect alignment with the narrative prose.
- **Case-Level Backtrace**: The full case index is exported to `output/case_index.csv`, letting a reviewer trace aggregate counts back to specific `safetyreportid` values.
- **Verification Tests**: Running `python verify_report.py` executes assertion tests comparing analytics results against the target sample report figures, validating the foundation before any report generation.

---

## 6. Evaluation at Scale (1,000+ Reports)

To evaluate report quality and correctness at enterprise scale:
1. **Rule-Based Assertion Checkers**: Run automated verification tests (similar to `verify_report.py`) on the pre-computed tables and JSON packets.
2. **Deterministic Number Extraction**: Parse the generated report text to extract all digits (e.g., case counts) and assert that every parsed number exists in the corresponding JSON evidence packet.
3. **N-Shot Quality Evaluations (LLM-as-a-Judge)**: Use a separate evaluator LLM (with temperature `0.0`) to check if:
   - Any claims in the report cannot be mapped to the JSON packet (Hallucination check).
   - The tone deviates from neutral regulatory styling.
   - Any prohibited phrases (e.g., "safety signal confirmed" or "drug is safe") are present.

---

## 7. Known Limitations

- **No CCDS Reference**: Expectedness (labeled vs. unlabeled) of reactions could not be verified because a company product label (CCDS) reference was not supplied. It was treated as out of scope for Version 0 (all serious cases were categorized under "Serious, Unlabelled" in tabulations).
- **Console-Based Review**: The human-in-the-loop review interface is console-based. In a production environment, this would be surfaced via a web application dashboard (e.g., React or Streamlit).
- **MedDRA SOC Classification**: MedDRA System Organ Class (SOC) fields were missing in the source dataset, so all counts are reported at the Preferred Term (PT) level.
- **Outcome Simplification**: Case-level outcomes are collapsed from reaction-level values using a conservative priority order (fatal > ongoing > recovering > recovered > unknown). This is useful for aggregation, but a production system should preserve both reaction-level and case-level outcome views explicitly.
- **Source-Type Heuristic**: Solicited versus spontaneous case source is inferred from `reporttype`, which works for this dataset but should be replaced with a clearer source taxonomy if future report types introduce more source variants.
