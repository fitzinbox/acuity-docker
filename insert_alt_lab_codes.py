#!/usr/bin/env python3
"""Insert map_custom_labcode_lookup rows for BCSTUDY01 and enable msr_use_alt_lab_codes.

Root cause of Hy's Law showing no data:
  LiverDatasetsDataProvider.getFilteredLabs() exact-matches lab_code.toUpperCase() against
  "ALANINE AMINOTRANSFERASE", "ASPARTATE AMINOTRANSFERASE", "TOTAL BILIRUBIN", "ALKALINE PHOSPHATASE".
  But result_laboratory.lab_code stores SDTM LBTESTCD short codes (ALT, AST, BILIRUBI, ALKALINE).

Fix: enable the CLL decode mechanism so LabRepository COALESCE resolves short codes to
canonical display names before LiverDatasetsDataProvider sees them. No ETL re-run needed —
the decode is read-time SQL via LEFT JOIN.

All 14 BCSTUDY01 lab codes mapped to human-readable names.
The four liver test names match LiverDatasetsDataProvider exactly (case-insensitive via .toUpperCase()).
"""
import subprocess
import sys

MSR_ID = 2   # BCSTUDY01

# (cll_labcode, cll_test_name, cll_sample_name)
# cll_test_name for liver tests must uppercase-match LiverDatasetsDataProvider:
#   "ALANINE AMINOTRANSFERASE", "ASPARTATE AMINOTRANSFERASE", "TOTAL BILIRUBIN", "ALKALINE PHOSPHATASE"
LAB_CODES = [
    # Chemistry
    ("ALT",      "Alanine Aminotransferase",  "Chemistry"),   # → ALANINE AMINOTRANSFERASE ✓
    ("AST",      "Aspartate Aminotransferase", "Chemistry"),  # → ASPARTATE AMINOTRANSFERASE ✓
    ("BILIRUBI", "Total Bilirubin",            "Chemistry"),  # → TOTAL BILIRUBIN ✓
    ("ALKALINE", "Alkaline Phosphatase",       "Chemistry"),  # → ALKALINE PHOSPHATASE ✓
    ("CA15-3",   "CA 15-3",                   "Chemistry"),
    ("CA27-29",  "CA 27-29",                  "Chemistry"),
    ("CREATINI", "Creatinine",                "Chemistry"),
    ("GLUCOSE",  "Glucose",                   "Chemistry"),
    ("POTASSIU", "Potassium",                 "Chemistry"),
    ("SODIUM",   "Sodium",                    "Chemistry"),
    # Haematology
    ("HAEMOGLO", "Haemoglobin",               "Haematology"),
    ("NEUTROPH", "Neutrophils",               "Haematology"),
    ("PLATELET", "Platelets",                 "Haematology"),
    ("WHITEBL",  "White Blood Cell Count",    "Haematology"),
]

insert_rows = "\n".join(
    f"INSERT INTO map_custom_labcode_lookup (cll_id, cll_labcode, cll_test_name, cll_sample_name, cll_msr_id)"
    f" VALUES (nextval('acuity.cll_seq'), '{labcode}', '{test_name}', '{sample_name}', {MSR_ID});"
    for labcode, test_name, sample_name in LAB_CODES
)

SQL = f"""SET search_path TO acuity;
BEGIN;

-- Insert CLL decode rows for all 14 BCSTUDY01 LBTESTCD codes
{insert_rows}

-- Enable the custom lab code decode mechanism for this study
UPDATE map_study_rule SET msr_use_alt_lab_codes = 1 WHERE msr_id = {MSR_ID};

COMMIT;
"""

VERIFY_SQL = f"""SET search_path TO acuity;
SELECT cll_labcode, cll_test_name, cll_sample_name FROM map_custom_labcode_lookup
  WHERE cll_msr_id = {MSR_ID} ORDER BY cll_sample_name, cll_labcode;
SELECT msr_use_alt_lab_codes FROM map_study_rule WHERE msr_id = {MSR_ID};

-- Simulate what LabRepository COALESCE will return for the four liver tests
SELECT lab_code AS raw_code,
       COALESCE(cll.cll_test_name, lab_code) AS resolved_name
FROM (SELECT DISTINCT lab_code FROM result_laboratory
      WHERE lab_code IN ('ALT','AST','BILIRUBI','ALKALINE')) codes
LEFT JOIN map_custom_labcode_lookup cll
  ON upper(codes.lab_code) = upper(cll.cll_labcode) AND cll.cll_msr_id = {MSR_ID};
"""


def run_psql(user, sql):
    return subprocess.run(
        ["docker", "exec", "-i", "acuity-docker-postgres-1",
         "psql", "-U", user, "-d", "acuity_db"],
        input=sql, capture_output=True, text=True
    )


if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        print(SQL)
        sys.exit(0)

    print("Inserting CLL rows and enabling msr_use_alt_lab_codes...")
    r = run_psql("acuity", SQL)
    inserts = r.stdout.count("INSERT 0 1")
    updates = r.stdout.count("UPDATE 1")
    print(f"  Return code: {r.returncode} — {inserts}/{len(LAB_CODES)} inserts, {updates}/1 update")
    if r.returncode != 0 or inserts < len(LAB_CODES) or updates < 1:
        print("STDOUT:", r.stdout[-2000:])
        print("STDERR:", r.stderr[-500:])
        sys.exit(1)

    print("\nVerifying CLL state + COALESCE simulation:")
    v = run_psql("acuity", VERIFY_SQL)
    print(v.stdout)
    if v.returncode != 0:
        print("STDERR:", v.stderr[-500:])
        sys.exit(1)
