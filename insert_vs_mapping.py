#!/usr/bin/env python3
"""Insert VS (Vitals) AdminUI mapping into the live acuity_db.

Root cause: VS.csv was added via AdminUI during initial smoke test and wiped by a
DB reset that also took LB (fixed in 0ca9e15). VS was never in the seed scripts.

Mapping uses mfd_id=33 (Vital source) — dual-entity, same pattern as LB/ECG:
  process_order=1: Test (men_id=15)     — mfi_ids 133/132/131/129/130
  process_order=2: VitalThin (men_id=38) — mfi_ids 434/435/436/437/438/439/440/824

Live DB explicit IDs (verified against current maxima before insertion):
  mfr_id = 149  (MAX was 148)
  mdf_id = 150  (MAX was 149)
  mmr_ids = 3057-3069  (MAX was 3056)
  mcr_ids = 3280-3292  (MAX was 3279)
"""
import subprocess
import sys

MFR_ID  = 149
MDF_ID  = 150
MFD_ID  = 33    # Vital source
MSR_ID  = 2     # BCSTUDY01
MFT_ID  = 1     # SAS file type

FIELDS = [
    # (mfi_id, csv_col, mmr_id, mcr_id)
    # Test entity (men_id=15, process_order=1)
    (133, "STUDYID",  3057, 3280),   # studyName
    (132, "STUDYID",  3058, 3281),   # part
    (131, "USUBJID",  3059, 3282),   # subject
    (129, "VISITNUM", 3060, 3283),   # visit
    (130, "VSDTC",    3061, 3284),   # date
    # VitalThin entity (men_id=38, process_order=2)
    (434, "STUDYID",  3062, 3285),   # studyName
    (435, "STUDYID",  3063, 3286),   # part
    (436, "USUBJID",  3064, 3287),   # subject
    (437, "VSDTC",    3065, 3288),   # date
    (438, "VSTESTCD", 3066, 3289),   # testName
    (439, "VSSTRESN", 3067, 3290),   # testResult
    (440, "VSSTRESU", 3068, 3291),   # resultUnit
    (824, "VISIT",    3069, 3292),   # protocolScheduleTimepoint
]

INSERT_SQL = f"""BEGIN;

-- File rule
INSERT INTO map_file_rule (mfr_id, mfr_name, mfr_enabled, mfr_is_updated, mfr_msr_id, mfr_mft_id)
  VALUES ({MFR_ID}, 'local://BCSTUDY01/VS.csv', 1, 1, {MSR_ID}, {MFT_ID});

-- File description link (drives AdminUI checklist)
INSERT INTO map_description_file (mdf_id, mdf_mfr_id, mdf_mfd_id)
  VALUES ({MDF_ID}, {MFR_ID}, {MFD_ID});

-- Mapping rules + field links + column rules
""" + "\n".join(
    f"""INSERT INTO map_mapping_rule (mmr_id, mmr_mfr_id, mmr_maf_id) VALUES ({mmr}, {MFR_ID}, 1);
INSERT INTO map_mapping_rule_field (mrf_id, mrf_mmr_id, mrf_mfi_id) VALUES ({mmr}, {mmr}, {mfi});
INSERT INTO map_column_rule (mcr_id, mcr_mmr_id, mcr_name) VALUES ({mcr}, {mmr}, '{col}');"""
    for mfi, col, mmr, mcr in FIELDS
) + "\n\nCOMMIT;"

SETVAL_SQL = """SET search_path TO acuity;
SELECT setval('mfr_seq', (SELECT MAX(mfr_id)::bigint FROM map_file_rule));
SELECT setval('mdf_seq', (SELECT MAX(mdf_id)::bigint FROM map_description_file));
SELECT setval('mmr_seq', (SELECT MAX(mmr_id)::bigint FROM map_mapping_rule));
SELECT setval('mrf_seq', (SELECT MAX(mrf_id)::bigint FROM map_mapping_rule_field));
SELECT setval('mcr_seq', (SELECT MAX(mcr_id)::bigint FROM map_column_rule));"""


def run_psql(user, sql):
    return subprocess.run(
        ["docker", "exec", "-i", "acuity-docker-postgres-1",
         "psql", "-U", user, "-d", "acuity_db"],
        input=sql, capture_output=True, text=True
    )


if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        print(INSERT_SQL)
        sys.exit(0)

    print("Inserting VS mapping as acuity user...")
    r = run_psql("acuity", INSERT_SQL)
    inserts = r.stdout.count("INSERT 0 1")
    print(f"  Return code: {r.returncode} — {inserts}/40 inserts succeeded")
    if r.returncode != 0 or inserts < 40:
        print("STDOUT:", r.stdout[-2000:])
        print("STDERR:", r.stderr[-500:])
        sys.exit(1)

    print("Advancing sequences as dbadmin...")
    sv = run_psql("dbadmin", SETVAL_SQL)
    if sv.returncode == 0:
        print("  Sequences advanced OK")
    else:
        print("  setval FAILED:", sv.stderr[-500:])
        sys.exit(1)

    print("Verifying insertion...")
    v = run_psql("acuity", f"""SET search_path TO acuity;
SELECT mfr_id, mfr_name, mfr_enabled FROM map_file_rule WHERE mfr_id = {MFR_ID};
SELECT COUNT(*) AS field_mappings FROM map_mapping_rule WHERE mmr_mfr_id = {MFR_ID};
SELECT COUNT(*) AS column_rules FROM map_mapping_rule mmr
  JOIN map_column_rule mcr ON mcr.mcr_mmr_id = mmr.mmr_id
  WHERE mmr.mmr_mfr_id = {MFR_ID};""")
    print(v.stdout)
