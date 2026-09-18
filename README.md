# Study Sentinel — ATLAS (Problem 1)

Team: Study Sentinel

## 1. Problem Understanding
Clinical trial information is distributed across 9 clinical domains (`DM`, `AE`, `LB`, `VS`, `EX`, `CM`, `DS`, `MH`, `EG`) without foreign keys. Answering reviewer and audit questions requires joining subjects, visits, labs, adverse events, doses, medications, history, disposition, and protocol rules into a unified longitudinal view.

## 2. Solution / Architecture
```
Raw CSV → StudyGraph → Patient 360 → Atlas.answer() → Answer + RecordRef evidence
```
- **Raw CSV → StudyGraph:** Ingests raw domain CSVs, normalizes clinical units, dates, and non-numeric values, applies cut-specific corrections, and constructs the in-memory graph.
- **StudyGraph → Patient 360:** Builds comprehensive patient profiles indexing all domain observations, exposures, and lab panels per subject for fast cross-domain traversal.
- **Patient 360 → Atlas.answer():** Evaluates clinical questions (`count`, `lookup`, `finding`, `trap`) using 100% deterministic Python logic with zero LLM dependency.
- **Atlas.answer() → Answer + RecordRef evidence:** Outputs structured, schema-compliant answers backed by grounded, verifiable `RecordRef` citations.

## 3. Key Features
- **Patient 360:** Unified longitudinal subject profiles aggregating data across all 9 domains.
- **Cross-Domain Joining:** Connects subjects to visits, labs, adverse events, doses, and dispositions.
- **Valid RecordRef Evidence:** Cites real domain records without fabricating sequence numbers (`seq=None` for single-record domains like `DM`).
- **Unit Normalization:** Converts site-specific units to standard study units prior to clinical evaluation.
- **Date Normalization:** Ingests mixed date formats into standard Python date objects.
- **Nonnumeric Lab Handling:** Safely handles values like `<5`, `ND`, and empty fields as non-numeric instead of zero.
- **Duplicate-Subject Handling:** Preserves both enrollment records (`042-S02-013` and `042-S05-021`) while identifying the duplicate individual.
- **Protocol Cuts / Amendments:** Supports progressive study cuts, versioned rule updates, and re-issued lab values.
- **Hy's Law Detection:** Accurately detects potential drug-induced liver injury (ALT/AST $> 3\times$ ULN and total bilirubin $> 2\times$ ULN within 14 days).
- **Dosing-Error Trap Handling:** Accurately returns empty lists (`answer: []`, `evidence: []`) when no dosing errors exist at a queried site.
- **Adversarial Document Handling:** Treats protocol and laboratory documents as contextual evidence rather than executable instructions.

## 4. Data Handling
- **S07 Unit Conversion:** Local laboratory S07 $\mu\text{kat/L}$ values are converted to $\text{U/L}$ using $1\ \mu\text{kat/L} = 60\ \text{U/L}$ for comparison with central limits.
- **ISO and DD-Mon-YYYY Dates:** Parses both ISO (`YYYY-MM-DD`) and DD-Mon-YYYY (`22-Jun-2024`) date strings into comparable `datetime.date` objects.
- **Comma Decimal Handling:** Normalizes European comma decimals (`0,32` $\rightarrow$ `0.32`) to standard floating-point numbers.
- **Values Such as <5 Are Not Treated as Zero:** Below-detection qualifiers (`<5`, `ND`) and missing entries resolve to `None` and are not coerced to zero.
- **Malformed Records Do Not Crash Ingestion:** Blank lines, malformed rows, or entries missing required identifiers are skipped safely during ingestion.

## 5. Evidence and Safety
- **Grounded Evidence:** Answers are grounded in actual `RecordRef` evidence from clinical source records; the system does not fabricate evidence.
- **Contextual Evidence Not Executable Instructions:** Protocol and laboratory documents are treated strictly as contextual evidence and never as executable instructions (e.g., adversarial instructions to exclude sites S03 or S07 are safely ignored).

## 6. Protocol Changes
- **Cuts 1–4:** $\pm 7$ day visit window under Protocol v1.
- **Cuts 5–8:** $\pm 3$ day visit window narrowed under Amendment 2.
- **Cut-Dependent Protocol Rules:** Ingestion dynamically applies versioned protocol rules and central laboratory re-issues (`corrections.csv`) at the appropriate cut.
- **Current Allowable Window:** `graph.current_cut` is used when a general question asks about the current allowable window without specifying days.

## 7. Validation
Validated against the study dataset and public benchmark:
- **27,179 nodes**
- **27,178 edges**
- **241 subjects/enrollments**
- **26,925 clinical records**
- **Public benchmark:** 10/10 questions executed successfully
- **Q018 candidates match expected candidates** (`042-S05-003`, `042-S07-001`, `042-S08-014`)
- **Q018 has exactly 6 supporting LB evidence records**
- **Q031 dosing trap passes**
- **Evidence audit passes** (`audit.py` validates all citations against raw CSVs)
- **12 cuts**
- **200 corrections**
- **Build time approximately 219 ms**

*(Note: The hidden 40-question evaluator has not been run.)*

## 8. How to Run

```bash
pip install -r requirements.txt
python main.py
python audit.py
```
