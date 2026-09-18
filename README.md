# Study Sentinel — ATLAS (Problem 1)

**Team:** Study Sentinel

---

## 1. Problem Understanding
Clinical trial data in STUDY-042 is distributed across 9 disjoint clinical domain tables (`DM`, `AE`, `LB`, `VS`, `EX`, `CM`, `DS`, `MH`, `EG`) without foreign keys. Answering reviewer questions requires connecting subjects, visits, laboratory measurements, adverse events, administered doses, concomitant medications, medical history, dispositions, and evolving study protocol rules.

## 2. Solution / Architecture
The architecture uses 100% deterministic Python logic with zero LLM dependency, ensuring fast, reproducible, and fully auditable execution:
```
Raw CSVs ──► StudyGraph.build() ──► Patient 360 ──► Atlas.answer() ──► Answer + RecordRef Evidence
```
- **`StudyGraph`:** Ingests raw CSVs, normalizes values, handles corrections, and constructs the study graph.
- **`Patient 360`:** Compiles the complete longitudinal medical record for each subject across all domains in $O(1)$ lookup time.
- **`Atlas`:** Evaluates clinical questions (count, lookup, finding, trap) and produces schema-compliant answers backed by grounded evidence.

## 3. Key Features
- **Patient 360 & Cross-Domain Joins:** Unified subject structure linking visits, labs, exposures, and dispositions.
- **Valid RecordRef Evidence:** Grounded in raw records without hallucinating sequence numbers (`domain`, `usubjid`, `seq`).
- **Unit Normalization:** Converts site-specific units to standard study units prior to clinical evaluation.
- **Date Normalization:** Ingests mixed date formats into standard Python `datetime.date` objects.
- **Non-Numeric Lab Handling:** Retains values like `<5` or `ND` as non-numeric rather than converting them to zero.
- **Duplicate-Subject Handling:** Preserves both enrollment records (`042-S02-013` / `042-S05-021`) while identifying the duplicate person.
- **Protocol Cuts & Amendments:** Supports study progression across cuts, including rule changes and re-issued lab values.
- **Hy's Law Detection:** Identifies liver injury candidates (ALT/AST $> 3\times$ ULN and total bilirubin $> 2\times$ ULN within 14 days).
- **Dosing-Error Trap Handling:** Accurately returns empty lists (`answer: []`, `evidence: []`) when no errors exist for a site.
- **Adversarial Document Handling:** Evaluates protocol and lab manuals as factual evidence rather than executable instructions.

## 4. Data Handling
- **S07 Unit Conversion:** Local laboratory `S07` reports ALT/AST in $\mu\text{kat/L}$. Converted using $1\ \mu\text{kat/L} = 60\ \text{U/L}$ for comparison with central limits.
- **Dates:** Accurately parses both ISO (`YYYY-MM-DD`) and British (`DD-Mon-YYYY`) date formats.
- **Comma Decimals:** Converts European comma decimals (`0,32` $\rightarrow$ `0.32`).
- **Below-Detection Values:** Values such as `<5`, `ND`, or blanks resolve to `None` and are not treated as zero.
- **Malformed Records:** Ingestion safely skips blank lines or rows missing essential fields (`USUBJID`) without crashing.

## 5. Evidence and Safety
- **Verifiable Evidence:** Answers cite verifiable `RecordRef` entries directly from source tables without fabricated sequence numbers (`seq=None` for single-row `DM` records).
- **Contextual Evidence:** Protocol and laboratory documents are treated as contextual reference data. Instructions directed at automated reviewers (such as excluding sites S03/S07) are ignored during clinical evaluation.

## 6. Protocol Changes
- **Visit Windows:** Protocol v1 (Cuts 1–4) specifies a $\pm 7\ \text{day}$ visit window; Amendment 2 (Cuts 5–12) narrows this to $\pm 3\ \text{days}$.
- **Cut-Dependent Logic:** When a question references the allowable visit window without a specific number of days, `graph.current_cut` dynamically applies the window in force.
- **Corrections:** Ingests and applies the 200 central laboratory re-issues from `corrections.csv` at Cut 5.

## 7. Validation
- **Graph Structure:** 27,179 nodes, 27,178 edges, 241 subjects/enrollments, 26,925 clinical records.
- **Indexing Speed:** In-memory graph build executes in approximately 219 ms (well within the 120-second per question limit).
- **Public Benchmark:** 10/10 public questions evaluated successfully in `stage1_public.json`.
- **Q018 (Hy's Law):** Correctly identifies candidates `042-S05-003`, `042-S07-001`, and `042-S08-014`, supported by exactly 6 clinical `LB` records.
- **Q031 (Trap):** Correctly returns `[]` with empty evidence and honest explanatory text.
- **Evidence Audit:** All evidence citations verified against source CSVs with `audit.py`.
- **Dataset Cuts:** Validated across 12 cuts and 200 corrections.
*(Note: The hidden 40-question evaluator has not yet been run.)*

## 8. How to Run

```bash
pip install -r requirements.txt
python main.py
python audit.py
```
