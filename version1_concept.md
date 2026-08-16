# Version 1 Concept: Config-Driven Safety Reporting

To scale the report generator from a hardcoded PADER prototype to a multi-report suite (supporting PSUR, DSUR, CSR, and PBRER), we propose decoupling the **report structure** from the **code execution**. 

Instead of writing new code for each report type, we express the differences as **configuration and data**.

---

## 1. Config-Driven Report Structure

A report type is defined by a JSON configuration file (e.g., `config/dsur_config.json`). The config specifies:
- The metadata of the report (name, frequency, authority).
- The list of sections in order.
- For each section, its input data requirements (dependencies) and its prompt template.

```json
{
  "report_type": "DSUR",
  "description": "Development Safety Update Report",
  "sections": [
    {
      "id": "reporting_period",
      "title": "1. Introduction and Reporting Period",
      "data_requirements": ["metadata"],
      "prompt_template": "prompts/dsur/intro.txt"
    },
    {
      "id": "subject_exposure",
      "title": "2. Estimated Cumulative Subject Exposure",
      "data_requirements": ["cumulative_exposure_stats", "subject_demographics"],
      "prompt_template": "prompts/dsur/exposure.txt"
    },
    {
      "id": "line_listings",
      "title": "3. Serious Adverse Reaction Line Listings",
      "data_requirements": ["sar_line_listings", "expectedness_tabulation"],
      "prompt_template": "prompts/dsur/listings.txt"
    }
  ]
}
```

---

## 2. Reusable Calculations and Context Engineering

We implement a registry of **reusable analysis functions** in `src/analytics/registry.py`. Each analysis function is decorated with a unique ID:

```python
@analysis_registry.register("subject_demographics")
def compute_subject_demographics(df):
    # Computes patient age/sex/country breakdowns for the trial cohort
    return { ... }
```

When a report is generated:
1. The orchestrator parses the report config.
2. It aggregates all `data_requirements` across all sections (e.g., `["metadata", "subject_demographics", ...]`).
3. It runs only the required analysis functions on the input dataset.
4. For each section, it compiles the subset of pre-computed analysis results into a scoped **evidence packet** (context engineering) and pairs it with the section's specific prompt template.

---

## 3. Dynamic Prompt Templates

Prompts are decoupled from the code and organized by report type:
- `prompts/pader/`
- `prompts/dsur/`
- `prompts/psur/`

The orchestrator dynamically loads the prompt from the path specified in the configuration, renders it with the evidence packet, and calls the LLM.

---

## 4. Lineage, Auditing, and Versioning

For enterprise regulatory compliance, every generated report must be fully auditable:
- **Input Hash**: A SHA-256 hash of the input dataset.
- **Config Hash**: A hash of the report configuration and prompt files used.
- **Model Signature**: The model ID, temperature, and API version.
- **Prose Traceability**: We append metadata comments to each section in the markdown containing the exact JSON evidence packet used. A reviewer can click any number and trace it to the pre-computed Python dict.

By shifting the report specification from Python code to JSON configuration, adding a new report type (like a DSUR) becomes a configuration task, leaving the core execution pipeline completely untouched.
