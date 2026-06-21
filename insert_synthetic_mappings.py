#!/usr/bin/env python3
"""Insert DB mappings for synthetic SDTM files into acuity_db.
File rules 139-146, mapping rules 2939+, column rules 3131+

Run from scratch on a fresh DB (after Flyway migrations + insert_mappings.py).
Assumes file rules 139-146 are NOT yet present.

Domains covered:
  139 FA → PrimaryTumourLocation      (mfd_id=15)
  140 CE → Death                      (mfd_id=14)
  141 PS → PerformanceStatus          (mfd_id=54)
  142 DE → DiseaseExtent              (mfd_id=46)
  143 LB → Laboratory                 (mfd_id=6)   ← dual-entity: Test + Laboratory
  144 DM → SubjectCharacteristic      (mfd_id=32)  ← ethnicity grouping
  145 PR → Radiotherapy               (mfd_id=23)  ← prior radiotherapy (CAPRX R)
  146 VS → Vital source               (mfd_id=33)  ← dual-entity: Test + VitalThin

Tuple format: (mfi_id, csv_col_or_None) or (mfi_id, csv_col_or_None, mmr_value)
  mfi_id    — map_field primary key
  csv_col   — CSV column name (None = no column rule; field gets default from mmr_value)
  mmr_value — constant default stored on the mapping rule (e.g. 'Previous')

IMPORTANT: setval requires dbadmin — run the printed setval SQL separately as dbadmin
after the inserts complete. The INSERT block runs as the acuity user.
"""
import subprocess, sys

MSR_ID = 2   # BCSTUDY01 study rule
MFT_ID = 1   # SAS data file type

# (file_rule_id, mfd_id, csv_path, [ (mfi_id, csv_col_or_None[, mmr_value]), ... ])
# part field maps to "STUDYID" so the AdminUI checklist shows green.
SYNTHETIC = [
    # FA → PrimaryTumourLocation (mfd_id=15, men_id=19)
    (139, 15, "local://BCSTUDY01/FA.csv", [
        (160, "STUDYID"),    # studyName (mandatory)
        (156, "STUDYID"),    # part (mandatory)
        (155, "USUBJID"),    # subject (mandatory)
        (157, "FAORRES"),    # primaryTumLocation (mandatory)
        (158, "FADTC"),      # originalDiagnosisDate
        (159, None),          # primaryTumLocationComment
    ]),
    # CE → Death (mfd_id=14, men_id=18)
    (140, 14, "local://BCSTUDY01/CE.csv", [
        (154, "STUDYID"),    # studyName (mandatory)
        (153, "STUDYID"),    # part (mandatory)
        (152, "USUBJID"),    # subject (mandatory)
        (151, "CESTDTC"),    # date (mandatory)
        (570, "CETERM"),     # cause
        (571, "CEDECOD"),    # designationOfCause
        (572, None),          # autopsyPerformed
        (573, None),          # relatedToInvestigationDisease
        (574, None),          # narrativeCause
        (575, None),          # preferredTerm
        (576, None),          # llt
        (577, None),          # hlt
        (578, None),          # soc
    ]),
    # PS → PerformanceStatus (mfd_id=54, men_id=59)
    (141, 54, "local://BCSTUDY01/PS.csv", [
        (707, "STUDYID"),    # studyName (mandatory)
        (708, "STUDYID"),    # part (mandatory)
        (709, "USUBJID"),    # subject (mandatory)
        (710, "VISITNUM"),   # visitNumber
        (711, "PSDTC"),      # visitDate
        (712, "PSDTC"),      # assessmentDate (mandatory)
        (713, "PSORRES"),    # performanceStatus (mandatory)
        (714, "PSTESTCD"),   # questionnaire (ECOG)
    ]),
    # DE → DiseaseExtent (mfd_id=46, men_id=51)
    (142, 46, "local://BCSTUDY01/DE.csv", [
        (621, "STUDYID"),    # studyName (mandatory)
        (622, "STUDYID"),    # part (mandatory)
        (623, "USUBJID"),    # subject (mandatory)
        (624, "DEMETADV"),   # metastaticLocallyAdvanced
        (625, "DESITE"),     # siteOfLocalMetastaticDisease (mandatory)
        (626, None),          # otherLocallyAdvancedSites
        (627, None),          # otherMetastaticSites
        (628, "DEDTC"),      # visitDate
        (629, None),          # recentProgressionDate
        (630, None),          # recurrenceOfEarlierCancer
    ]),
    # LB → Laboratory (mfd_id=6)
    # Two entities: Test (men_id=15, process_order=1) then Laboratory (men_id=8, process_order=2).
    # BOTH must have field mappings in the same file rule or Lab rows aren't created.
    # sourceType maps to LBCAT (HAEMATOLOGY/CHEMISTRY); Laboratory.complete() capitalises it.
    (143, 6, "local://BCSTUDY01/LB.csv", [
        # Test entity fields (men_id=15, process_order=1) — MUST come first
        (133, "STUDYID"),    # studyName (mandatory)
        (132, "STUDYID"),    # part (mandatory)
        (131, "USUBJID"),    # subject (mandatory)
        (129, "VISITNUM"),   # visit
        (130, "LBDTC"),      # date (mandatory)
        # Laboratory entity fields (men_id=8, process_order=2)
        (68, "STUDYID"),     # studyName (mandatory)
        (66, "STUDYID"),     # part (mandatory)
        (65, "USUBJID"),     # subject (mandatory)
        (67, "LBDTC"),       # date (mandatory)
        (59, "LBTESTCD"),    # labCode (mandatory)
        (953, "LBCAT"),      # sourceType (mandatory — HAEMATOLOGY/CHEMISTRY)
        (61, "LBSTRESN"),    # laboratoryValue
        (62, "LBSTRESU"),    # laboratoryUnit
        (63, "LBNRLO"),      # refLow
        (64, "LBNRHI"),      # refHigh
        (784, "VISIT"),      # protocolScheduleTimepoint
    ]),
    # DM → SubjectCharacteristic (mfd_id=32, men_id=37) — ethnicity grouping
    # Populates result_sc; ethpop=ETHNIC gives the ethnicity value per subject.
    (144, 32, "local://BCSTUDY01/DM.csv", [
        (423, "STUDYID"),    # studyName (mandatory)
        (424, "STUDYID"),    # part (mandatory)
        (425, "USUBJID"),    # subject (mandatory)
        (426, None),          # visitNumber
        (427, None),          # visitDate
        (428, "ETHNIC"),     # ethpop → ethnicity value
        (429, None),          # sEthpop
    ]),
    # PR → Radiotherapy (mfd_id=23, men_id=26) — prior radiotherapy (CAPRX R in SSV)
    # radioTimeStatus must be 'Previous' (constant default) so RadiotherapyService
    # filter passes: .filter(r -> "Previous".equalsIgnoreCase(r.getEvent().getTimeStatus()))
    (145, 23, "local://BCSTUDY01/PR.csv", [
        (242, "STUDYID"),          # studyName (mandatory)
        (219, "STUDYID"),          # part (mandatory)
        (220, "USUBJID"),          # subject (mandatory)
        (223, "PRTRT"),            # radiotherapyGiven
        (224, "PRLOC"),            # radioSiteOrRegion
        (225, "PRENDTC"),          # radioEndDate
        (226, "PRSTDTC"),          # radioStartDate
        (227, None),                # treatmentStatus
        (228, "PRDOSE"),           # radiationDose
        (229, "PRNFRAC"),          # numberOfDoses
        (290, None, "Previous"),   # radioTimeStatus — constant default, no CSV column
    ]),
    # VS → Vital source (mfd_id=33) — dual-entity: Test (process_order=1) + VitalThin (process_order=2)
    # SDTM thin format: one row per measurement (VSTESTCD = SYSBP/DIABP/PULSE/TEMP/WEIGHT/HEIGHT).
    # testName (mfi_id 438) → VSTESTCD drives which vit_test_name row is created in result_vitals.
    # Originally added via AdminUI; re-seeded here so a DB reset doesn't silently wipe it.
    (146, 33, "local://BCSTUDY01/VS.csv", [
        # Test entity fields (men_id=15, process_order=1) — MUST be mapped or VitalThin rows aren't created
        (133, "STUDYID"),    # studyName (mandatory)
        (132, "STUDYID"),    # part (mandatory)
        (131, "USUBJID"),    # subject (mandatory)
        (129, "VISITNUM"),   # visit
        (130, "VSDTC"),      # date (mandatory)
        # VitalThin entity fields (men_id=38, process_order=2)
        (434, "STUDYID"),    # studyName (mandatory)
        (435, "STUDYID"),    # part (mandatory)
        (436, "USUBJID"),    # subject (mandatory)
        (437, "VSDTC"),      # date (mandatory)
        (438, "VSTESTCD"),   # testName (mandatory — SYSBP/DIABP/PULSE/TEMP/WEIGHT/HEIGHT)
        (439, "VSSTRESN"),   # testResult
        (440, "VSSTRESU"),   # resultUnit
        (824, "VISIT"),      # protocolScheduleTimepoint
    ]),
]

def build_sql():
    insert_lines = ["BEGIN;"]
    setval_lines = []  # run separately as dbadmin (acuity user lacks setval permission)

    # File rules
    insert_lines.append("\n-- ===== FILE RULES =====")
    for (mfr_id, mfd_id, csv_path, fields) in SYNTHETIC:
        insert_lines.append(
            f"INSERT INTO map_file_rule (mfr_id, mfr_name, mfr_enabled, mfr_is_updated, mfr_msr_id, mfr_mft_id)"
            f" VALUES ({mfr_id}, '{csv_path}', 1, 1, {MSR_ID}, {MFT_ID});"
        )

    # map_description_file (links file rule to file description — drives checklist)
    insert_lines.append("\n-- ===== FILE DESCRIPTION LINKS (checklist) =====")
    for (mfr_id, mfd_id, csv_path, fields) in SYNTHETIC:
        insert_lines.append(
            f"INSERT INTO map_description_file (mdf_id, mdf_mfr_id, mdf_mfd_id)"
            f" VALUES ({mfr_id}, {mfr_id}, {mfd_id});"
        )

    # Mapping rules + field links + column rules
    insert_lines.append("\n-- ===== MAPPING RULES =====")
    mmr_id = 2939
    mcr_id = 3131
    for (mfr_id, mfd_id, csv_path, fields) in SYNTHETIC:
        insert_lines.append(f"\n-- mfr_id={mfr_id} ({csv_path})")
        for field in fields:
            mfi_id  = field[0]
            csv_col = field[1]
            mmr_val = field[2] if len(field) > 2 else None
            if mmr_val is not None:
                insert_lines.append(
                    f"INSERT INTO map_mapping_rule (mmr_id, mmr_mfr_id, mmr_maf_id, mmr_value)"
                    f" VALUES ({mmr_id}, {mfr_id}, 1, '{mmr_val}');"
                )
            else:
                insert_lines.append(
                    f"INSERT INTO map_mapping_rule (mmr_id, mmr_mfr_id, mmr_maf_id)"
                    f" VALUES ({mmr_id}, {mfr_id}, 1);"
                )
            insert_lines.append(
                f"INSERT INTO map_mapping_rule_field (mrf_id, mrf_mmr_id, mrf_mfi_id)"
                f" VALUES ({mmr_id}, {mmr_id}, {mfi_id});"
            )
            if csv_col is not None:
                insert_lines.append(
                    f"INSERT INTO map_column_rule (mcr_id, mcr_mmr_id, mcr_name)"
                    f" VALUES ({mcr_id}, {mmr_id}, '{csv_col}');"
                )
                mcr_id += 1
            mmr_id += 1

    insert_lines.append("\nCOMMIT;")

    # setval must run as dbadmin (acuity user only has rU on sequences, not w)
    setval_lines = [
        "SET search_path TO acuity;",
        "SELECT setval('mcr_seq', (SELECT MAX(mcr_id)::bigint FROM map_column_rule));",
        "SELECT setval('mmr_seq', (SELECT MAX(mmr_id)::bigint FROM map_mapping_rule));",
        "SELECT setval('mrf_seq', (SELECT MAX(mrf_id)::bigint FROM map_mapping_rule_field));",
        "SELECT setval('mfr_seq', (SELECT MAX(mfr_id)::bigint FROM map_file_rule));",
        "SELECT setval('mdf_seq', (SELECT MAX(mdf_id)::bigint FROM map_description_file));",
    ]

    return "\n".join(insert_lines), "\n".join(setval_lines), mmr_id, mcr_id


if __name__ == "__main__":
    sql, setval_sql, final_mmr, final_mcr = build_sql()
    print(f"Generated SQL: mmr_ids 2939-{final_mmr-1}, mcr_ids 3131-{final_mcr-1}")

    if "--dry-run" in sys.argv:
        for line in sql.split("\n")[:40]:
            print(line)
        sys.exit(0)

    print("Executing INSERT SQL as acuity user...")
    result = subprocess.run(
        ["docker", "exec", "-i", "acuity-docker-postgres-1",
         "psql", "-U", "acuity", "-d", "acuity_db"],
        input=sql, capture_output=True, text=True
    )
    successes = result.stdout.count("INSERT 0 1")
    print(f"Return code: {result.returncode} — {successes} inserts succeeded")
    if result.returncode != 0:
        print("STDOUT:", result.stdout[-2000:])
        print("STDERR:", result.stderr[-500:])
        sys.exit(1)

    print("Advancing sequences as dbadmin...")
    sv_result = subprocess.run(
        ["docker", "exec", "-i", "acuity-docker-postgres-1",
         "psql", "-U", "dbadmin", "-d", "acuity_db"],
        input=setval_sql, capture_output=True, text=True
    )
    if sv_result.returncode == 0:
        print("Sequences advanced OK")
    else:
        print("setval FAILED (sequences may need manual reset):")
        print(sv_result.stderr[-500:])
