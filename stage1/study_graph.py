"""
stage1/study_graph.py

StudyGraph implementation for ATLAS Problem 1.
Loads, normalizes, and indexes clinical trial data once to support:
  - Fast Patient 360 lookups
  - Multiple date format handling (ISO and DD-Mon-YYYY)
  - Unit normalization (e.g. S07 ukat/L -> U/L)
  - Comma-decimal cleaning (e.g. '0,32' -> 0.32)
  - Non-numeric lab handling ('<5', 'ND', blanks without converting to 0)
  - Missing field & malformed row tolerance
  - Cut-aware filtering & corrections
"""

import os
import csv
import re
import time
from datetime import date
from typing import Optional, Dict, Any, List


# Month map for DD-Mon-YYYY date strings
MONTH_MAP = {
    'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
    'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
}


def parse_date(date_str: Any) -> Optional[date]:
    """
    Parses various clinical date formats into standard datetime.date:
      - '2026-03-30' (YYYY-MM-DD)
      - '30-Mar-2026' or '28-May-1953' (DD-Mon-YYYY)
      - '2026/03/30' (YYYY/MM/DD)
    Returns None if empty or unparseable.
    """
    if not date_str or not isinstance(date_str, str):
        return None
    s = date_str.strip()
    if not s:
        return None

    # Try ISO YYYY-MM-DD
    m_iso = re.match(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})', s)
    if m_iso:
        try:
            return date(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
        except ValueError:
            return None

    # Try DD-Mon-YYYY (e.g., 28-May-1953 or 30-MAR-2026)
    m_mon = re.match(r'^(\d{1,2})-([A-Za-z]{3})-(\d{4})', s)
    if m_mon:
        day = int(m_mon.group(1))
        mon_str = m_mon.group(2).upper()
        year = int(m_mon.group(3))
        month = MONTH_MAP.get(mon_str)
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                return None

    return None


def parse_number(val_str: Any) -> Optional[float]:
    """
    Safely converts strings to float:
      - '12.4' -> 12.4
      - '12,4' -> 12.4 (European comma)
      - '<5', 'ND', '' -> None (not 0!)
    """
    if val_str is None:
        return None
    s = str(val_str).strip()
    if not s or s == 'ND' or s.startswith('<') or s.startswith('>'):
        return None
    # Replace comma decimal with dot
    s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


class StudyGraph:
    """
    StudyGraph indexes all 9 clinical tables into a subject-centered graph.
    """

    DOMAINS = ["DM", "AE", "LB", "VS", "EX", "CM", "DS", "MH", "EG"]

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        # Resolve csv data folder (could be data_dir or data_dir/data)
        if os.path.isdir(os.path.join(data_dir, "data")):
            self.csv_dir = os.path.join(data_dir, "data")
        else:
            self.csv_dir = data_dir

        self.tables: Dict[str, List[Dict[str, Any]]] = {}
        self.reference_ranges: List[Dict[str, Any]] = []
        self.corrections: List[Dict[str, Any]] = []
        self.cuts: List[Dict[str, Any]] = []
        
        # Subject-centered index: usubjid -> dict of domains
        self.subjects: Dict[str, Dict[str, Any]] = {}
        self.stats: Dict[str, Any] = {}
        self.current_cut: Optional[int] = None

    def _read_csv(self, filename: str) -> List[Dict[str, Any]]:
        """Reads a CSV safely, skipping malformed rows and stripping whitespace."""
        filepath = os.path.join(self.csv_dir, filename)
        if not os.path.exists(filepath):
            return []

        records = []
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            try:
                header = [col.strip() for col in next(reader)]
            except StopIteration:
                return []

            for row in reader:
                if not row or len(row) != len(header):
                    # Skip malformed or empty rows
                    continue
                record = {header[i]: row[i].strip() for i in range(len(header))}
                records.append(record)

        return records

    def build(self, cut: Optional[int] = None) -> Dict[str, Any]:
        """
        Builds and indexes the study graph.
        If cut is provided, filters data to cut_available <= cut
        and applies corrections up to that cut.
        """
        start_time = time.time()
        self.current_cut = cut
        self.subjects.clear()
        self.tables.clear()

        # 1. Load reference data
        self.reference_ranges = self._read_csv("reference_ranges.csv")
        self.corrections = self._read_csv("corrections.csv")
        self.cuts = self._read_csv("cuts.csv")

        # 2. Pre-index corrections: (cut, domain, usubjid, seq, field) -> new_value
        corrections_map: Dict[tuple, str] = {}
        for corr in self.corrections:
            corr_cut = int(corr.get("cut", 999))
            if cut is None or corr_cut <= cut:
                domain = corr.get("domain", "").upper()
                usubjid = corr.get("usubjid", "")
                seq = corr.get("seq", "")
                field = corr.get("field", "")
                new_val = corr.get("new_value", "")
                corrections_map[(domain, usubjid, seq, field)] = new_val

        # 3. Load and normalize each clinical domain
        node_count = 1  # root study node
        edge_count = 0
        visited_sites = set()

        for domain in self.DOMAINS:
            fname = f"{domain}.csv"
            raw_records = self._read_csv(fname)
            processed_records = []

            for rec in raw_records:
                usubjid = rec.get("USUBJID", "")
                if not usubjid:
                    continue

                # Filter by cut if requested
                cut_avail_str = rec.get("cut_available", "")
                if cut is not None and cut_avail_str:
                    try:
                        if int(cut_avail_str) > cut:
                            continue
                    except ValueError:
                        pass

                # Extract sequence number
                seq_col = f"{domain}SEQ"
                seq_val = None
                if seq_col in rec and rec[seq_col].isdigit():
                    seq_val = int(rec[seq_col])
                    rec["SEQ"] = seq_val
                elif "SEQ" in rec and rec["SEQ"].isdigit():
                    seq_val = int(rec["SEQ"])
                    rec["SEQ"] = seq_val

                # Apply corrections if applicable
                if seq_val is not None:
                    for field_name in list(rec.keys()):
                        key = (domain, usubjid, str(seq_val), field_name)
                        if key in corrections_map:
                            rec[field_name] = corrections_map[key]
                            rec["_corrected"] = True

                # Parse and normalize dates in record
                for k, v in list(rec.items()):
                    if "DTC" in k.upper() or "DATE" in k.upper():
                        parsed_d = parse_date(v)
                        if parsed_d:
                            rec[f"{k}_PARSED"] = parsed_d

                # Domain-specific normalizations
                if domain == "LB":
                    self._normalize_lab_record(rec)
                elif domain in ["VS", "EG", "EX"]:
                    self._normalize_numeric_fields(rec, domain)

                # Track unique sites from DM or USUBJID
                site_id = rec.get("SITEID") or usubjid.split("-")[1] if "-" in usubjid else "UNKNOWN"
                rec["SITEID"] = site_id
                visited_sites.add(site_id)

                processed_records.append(rec)

            self.tables[domain] = processed_records

        # 4. Build Subject-Centered Graph Index (Patient 360)
        dm_records = self.tables.get("DM", [])
        for dm in dm_records:
            u = dm["USUBJID"]
            self.subjects[u] = {
                "usubjid": u,
                "site_id": dm.get("SITEID", ""),
                "demographics": dm,
                "adverse_events": [],
                "labs": [],
                "vitals": [],
                "exposure": [],
                "medications": [],
                "disposition": None,
                "history": [],
                "ecg": [],
            }

        # Associate domain records to subjects
        domain_key_map = {
            "AE": "adverse_events",
            "LB": "labs",
            "VS": "vitals",
            "EX": "exposure",
            "CM": "medications",
            "MH": "history",
            "EG": "ecg",
        }

        for domain, key in domain_key_map.items():
            for rec in self.tables.get(domain, []):
                u = rec["USUBJID"]
                if u not in self.subjects:
                    # Subject in domain table but missing in DM
                    site_id = rec.get("SITEID", "")
                    self.subjects[u] = {
                        "usubjid": u,
                        "site_id": site_id,
                        "demographics": None,
                        "adverse_events": [],
                        "labs": [],
                        "vitals": [],
                        "exposure": [],
                        "medications": [],
                        "disposition": None,
                        "history": [],
                        "ecg": [],
                    }
                self.subjects[u][key].append(rec)

        # Disposition (one per subject)
        for ds in self.tables.get("DS", []):
            u = ds["USUBJID"]
            if u in self.subjects:
                self.subjects[u]["disposition"] = ds

        # 5. Compute graph node and edge counts
        # Nodes: 1 (study) + sites + subjects + records
        num_subjects = len(self.subjects)
        num_sites = len(visited_sites)
        total_records = sum(len(records) for records in self.tables.values())

        # Edges: study -> site, site -> subject, subject -> records
        node_count = 1 + num_sites + num_subjects + total_records
        edge_count = num_sites + num_subjects + total_records

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        self.stats = {
            "nodes": node_count,
            "edges": edge_count,
            "subjects": num_subjects,
            "sites": num_sites,
            "total_records": total_records,
            "build_time_ms": elapsed_ms,
            "cut": cut,
        }

        return self.stats

    def _normalize_lab_record(self, rec: Dict[str, Any]) -> None:
        """
        Normalizes laboratory results:
          1. Cleans comma decimals: '3,995' -> 3.995
          2. Handles S07 local lab unit: ukat/L -> U/L (factor 60)
          3. Stores LB_NUM_VAL, LB_STD_VAL, LB_STD_UNIT
        """
        raw_res = rec.get("LBORRES", "")
        raw_unit = rec.get("LBORRESU", "").strip()
        test_cd = rec.get("LBTESTCD", "").strip().upper()
        site_id = rec.get("SITEID", "")

        num_val = parse_number(raw_res)
        rec["LB_NUM_VAL"] = num_val

        if num_val is not None:
            # Check for Site S07 local lab conversion: ukat/L -> U/L
            if raw_unit == "ukat/L" or (site_id == "S07" and test_cd in ["ALT", "AST"]):
                rec["LB_STD_VAL"] = round(num_val * 60.0, 3)
                rec["LB_STD_UNIT"] = "U/L"
                rec["LB_CONVERTED"] = True
            else:
                rec["LB_STD_VAL"] = num_val
                rec["LB_STD_UNIT"] = raw_unit
                rec["LB_CONVERTED"] = False
        else:
            rec["LB_STD_VAL"] = None
            rec["LB_STD_UNIT"] = raw_unit
            rec["LB_CONVERTED"] = False

    def _normalize_numeric_fields(self, rec: Dict[str, Any], domain: str) -> None:
        """Parses numeric values for VS, EG, and EX."""
        val_col = f"{domain}ORRES" if domain in ["VS", "EG"] else "EXDOSE"
        if val_col in rec:
            rec[f"{val_col}_NUM"] = parse_number(rec[val_col])

    def patient360(self, usubjid: str) -> Dict[str, Any]:
        """
        Patient 360 view: Returns complete interconnected history for a subject.
        """
        return self.subjects.get(usubjid, {})
