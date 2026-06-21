#!/usr/bin/env python3
"""
Generate and execute DB INSERT statements for BCSTUDY01 domain mappings.
Covers: CM, DS, MH, SH, RS, TR, TU, EC, PC, TP, SG, PR, PP, BS, GE
"""

import subprocess
import sys

MSR_ID = 2          # BCSTUDY01 study rule ID
MFT_ID = 1          # SAS data file type
MFR_AGG_FUN = 1     # default aggregation function (mmr_maf_id)

# Starting IDs (must be > current maxima)
# map_file_rule max=123, map_mapping_rule max=2701, map_column_rule max=3015

NEXT_FILE_RULE_ID = [124]
NEXT_MMR_ID = [2702]
NEXT_MCR_ID = [3016]

def next_fr():
    r = NEXT_FILE_RULE_ID[0]; NEXT_FILE_RULE_ID[0] += 1; return r

def next_mmr():
    r = NEXT_MMR_ID[0]; NEXT_MMR_ID[0] += 1; return r

def next_mcr():
    r = NEXT_MCR_ID[0]; NEXT_MCR_ID[0] += 1; return r


# Domain definitions:
# (name, mfd_id, csv_file, [ (men_id, process_order, [(mfi_id, csv_col_or_None), ...]), ...] )
# Fields listed in mfi_order sequence (matching DB order)
DOMAINS = [

    # CM — Concomitant Medications → Medicine + ConcomitantMedSchedule
    # Note: Medicine entity has no 'part' field — only studyName/drugName/drugParent
    ("CM", 10, "local://BCSTUDY01/CM.csv", [
        (12, 1, [  # Medicine
            (98, "CMTRT"),      # drugName
            (99, None),          # drugParent
            (100, "STUDYID"),    # studyName
        ]),
        (3, 2, [  # ConcomitantMedSchedule
            (31, "STUDYID"),    # studyName
            (28, "STUDYID"),     # part
            (27, "USUBJID"),    # subject
            (589, None),         # aeNum
            (586, "CMROUTE"),   # route
            (29, "CMTRT"),      # drugName
            (661, None),         # atcCodeText
            (30, None),          # drugParent
            (20, "CMDOSE"),     # dose
            (581, None),         # doseTotal
            (21, "CMDOSU"),     # doseUnit
            (582, None),         # doseUnitOther
            (584, None),         # frequencyOther
            (22, None),          # frequency
            (23, None),          # atcCode
            (24, "CMSTDTC"),    # startDate
            (25, "CMENDTC"),    # endDate
            (26, "CMDECOD"),    # treatmentReason → decoded drug name
            (827, None),         # therapyReason
            (587, None),         # therapyReasonOther
            (588, None),         # prophylaxisSpecOther
            (820, None),         # infBodySys
            (821, None),         # infBodySysOther
            (818, None),         # activeIngredient1
            (819, None),         # activeIngredient2
            (822, None),         # reasonStop
            (823, None),         # reasonStopOther
        ]),
    ]),

    # DS — Disposition/Withdrawal → WithdrawalCompletion
    ("DS", 31, "local://BCSTUDY01/DS.csv", [
        (34, 1, [  # WithdrawalCompletion
            (408, "STUDYID"),   # studyName
            (409, "STUDYID"),    # part
            (410, "USUBJID"),   # subject
            (411, "DSDTC"),     # withdrawalCompletionDate
            (412, "DSTERM"),    # prematurelyWithdrawn → DSTERM (completion/withdrawal term)
            (413, "DSDECOD"),   # mainReason → DSDECOD (decoded reason)
            (414, None),         # specification
        ]),
    ]),

    # MH — Medical History → MedicalHistory
    ("MH", 43, "local://BCSTUDY01/MH.csv", [
        (48, 1, [  # MedicalHistory
            (554, "STUDYID"),   # studyName
            (555, "STUDYID"),    # part
            (556, "USUBJID"),   # subject
            (858, None),         # category (MHSCAT not present in MH.csv)
            (859, "MHTERM"),    # term
            (561, "MHONGO"),    # conditionStatus → ongoing flag
            (563, "MHSTDTC"),   # startDate
            (564, "MHENDTC"),   # endDate
            (565, None),         # lltName
            (566, "MHDECOD"),   # ptName → decoded preferred term
            (567, None),         # hltName
            (568, "MHBODSYS"),  # socName → body system
            (569, None),         # currentMedication
        ]),
    ]),

    # SH — Surgical History → SurgicalHistory
    ("SH", 45, "local://BCSTUDY01/SH.csv", [
        (50, 1, [  # SurgicalHistory
            (610, "STUDYID"),   # studyName
            (611, "STUDYID"),    # part
            (612, "USUBJID"),   # subject
            (613, "SHTERM"),    # procedure
            (614, "SHSTDTC"),   # startDate
            (616, None),         # hlt
            (617, None),         # llt
            (618, "SHDECOD"),   # pt → decoded procedure term
            (619, None),         # soc
            (620, "SHONGO"),    # current → ongoing flag
        ]),
    ]),

    # RS — RECIST Assessment → RecistAssessment
    ("RS", 16, "local://BCSTUDY01/RS.csv", [
        (20, 1, [  # RecistAssessment
            (171, "STUDYID"),   # studyName
            (162, "STUDYID"),    # part
            (161, "USUBJID"),   # subject
            (166, "RSDTC"),     # visitDate → assessment date
            (194, "VISITNUM"),  # visit → visit number
            (163, None),         # newLesionsSinceBaseline
            (164, None),         # newLesionSite
            (165, None),         # newLesionDate
            (167, "RSORRES"),   # overallRecistResponse
            (168, "RSINVAGR"),  # invAgreeWithRecistResponse
            (169, "RSINVRESP"), # invOpinion
            (170, None),         # reasonAssessmentsDiffer
            (218, None),         # assessmentFrequency
        ]),
    ]),

    # TR — Target Lesion → RecistTargetLesion
    ("TR", 25, "local://BCSTUDY01/TR.csv", [
        (28, 1, [  # RecistTargetLesion
            (250, "STUDYID"),   # studyName
            (251, "STUDYID"),    # part
            (252, "USUBJID"),   # subject
            (253, "TRDTC"),     # lesionDate
            (254, "TRLOC"),     # lesionSite
            (255, "TRLNKID"),   # lesionNumber
            (256, None),         # lesionPresent
            (257, "TRSTRESN"),  # lesionDiameter
            (259, "TRDTC"),     # visitDate (reuse TRDTC)
            (260, "VISITNUM"),  # visitNumber
            (258, None),         # investigatorsResponse
            (987, None),         # lesionNoLongerMeasurable
            (988, None),         # methodOfAssessment → not in TR.csv
        ]),
    ]),

    # TU — Tumour Identification → RecistNonTargetLesion
    ("TU", 26, "local://BCSTUDY01/TU.csv", [
        (29, 1, [  # RecistNonTargetLesion
            (270, "STUDYID"),   # studyName
            (271, "STUDYID"),    # part
            (272, "USUBJID"),   # subject
            (273, "TUDTC"),     # lesionDate
            (274, "TULOC"),     # lesionSite
            (276, None),         # lesionPresent
            (277, "TUORRES"),   # response
            (279, "TUDTC"),     # visitDate (reuse TUDTC)
            (280, "VISITNUM"),  # visitNumber
        ]),
    ]),

    # EC — ECG → Test + EG
    ("EC", 34, "local://BCSTUDY01/EC.csv", [
        (15, 1, [  # Test
            (133, "STUDYID"),   # studyName
            (132, "STUDYID"),    # part
            (131, "USUBJID"),   # subject
            (129, "VISITNUM"),  # visit
            (130, "ECDTC"),     # date
        ]),
        (39, 2, [  # EG
            (446, "STUDYID"),   # studyName
            (447, "STUDYID"),    # part
            (448, "USUBJID"),   # subject
            (449, "ECDTC"),     # date
            (450, "ECTESTCD"),  # testName
            (451, "ECSTRESN"),  # testResult
            (452, "ECSTRESU"),  # resultUnit
            (453, "ECNRIND"),   # evaluation → normal range indicator
            (454, None),         # abnormality
            (515, None),         # significant
            (857, None),         # protocolScheduleTimePoint
            (840, None),         # dateOfLastDose
            (841, None),         # lastDoseAmount
            (842, None),         # method
            (843, None),         # atrialFibrillation
            (844, None),         # sinusRhythm
            (845, None),         # reasonNoSinusRhythm
            (846, None),         # heartRhythm
            (847, None),         # heartRhythmOther
            (848, None),         # extraSystoles
            (849, None),         # specifyExtraSystoles
            (850, None),         # typeOfConduction
            (851, None),         # conduction
            (852, None),         # reasonAbnormalConduction
            (853, None),         # sttChanges
            (854, None),         # stSegment
            (855, None),         # tWave
        ]),
    ]),

    # PC — PK Concentration → PkConcentration
    ("PC", 29, "local://BCSTUDY01/PC.csv", [
        (32, 1, [  # PkConcentration
            (326, "STUDYID"),   # studyName
            (327, "STUDYID"),    # part
            (328, "USUBJID"),   # subject
            (338, "PCREFID"),   # spcIdentifier
            (331, "PCTESTCD"),  # analyte → test code
            (332, "PCSTRESN"),  # analyteConcentration
            (333, "PCSTRESU"),  # analyteConcentrationUnit
            (334, "PCLLOQ"),    # lowerLimit
            (335, None),         # treatmentCycle
            (336, None),         # treatment
            (337, None),         # treatmentSchedule
            (342, None),         # comment
        ]),
    ]),

    # TP — Tumour Pathology → Pathology (wide format: one row per subject)
    # Columns: STUDYID, DOMAIN, USUBJID, TPSEQ, TPDTC, HIST, GRADE, T, N, M
    # ERSTAT/PRSTAT/HER2STAT/KI67 are in SG.csv instead (no clean Pathology field for them)
    ("TP", 44, "local://BCSTUDY01/TP.csv", [
        (49, 1, [  # Pathology
            (601, "STUDYID"),   # studyName
            (602, "STUDYID"),    # part
            (603, "USUBJID"),   # subject
            (590, "TPDTC"),     # date
            (591, "HIST"),      # histologyType
            (592, None),         # histologyTypeDetails (no column)
            (593, "GRADE"),     # tumourGrade
            (594, None),         # stage (no column — derivable from T/N/M)
            (595, None),         # tumorLocation
            (596, "T"),          # primaryTumourStatus (pT1–pT4)
            (597, "N"),          # nodesStatus (pN0–pN3)
            (598, "M"),          # metastasesStatus (M0/M1)
            (599, None),         # methodOfDetermination
            (600, None),         # otherMethods
        ]),
    ]),

    # SG — Subject Groupings → PatientGroup (long and thin)
    # Uses PatientGroup (mfd_id=20, men_id=23) NOT SubjectCharacteristic (mfd_id=32).
    # PatientGroup stores one row per grouping×subject — exactly what SG.csv has.
    ("SG", 20, "local://BCSTUDY01/SG.csv", [
        (23, 1, [  # PatientGroup
            (188, "STUDYID"),   # studyName
            (190, "STUDYID"),   # part
            (189, "USUBJID"),   # subject
            (193, "SGCAT"),     # groupingName → grouping category
            (191, "SGORRES"),   # groupName → grouping result
        ]),
    ]),

    # PR — Procedures → Chemotherapy
    ("PR", 24, "local://BCSTUDY01/PR.csv", [
        (27, 1, [  # Chemotherapy
            (230, "STUDYID"),   # studyName
            (231, "STUDYID"),    # part
            (232, "USUBJID"),   # subject
            (235, "PRTRT"),     # preferredNameOfMed
            (236, "PRSTDTC"),   # chemoStartDate
            (237, "PRENDTC"),   # chemoEndDate
            (238, None),         # numberOfCycles
            (239, "PRCAT"),     # chemoClass → procedure category
            (240, None),         # treatmentStatus
            (241, None),         # bestResponse
            (243, None),         # reasonForFailure
            (244, None, "Previous"),  # chemoTimeStatus — constant default, no CSV column
            (245, None),         # concomitantTherapy
            (246, None),         # numberOfPriorRegiments
            (247, "PRDECOD"),   # cancerTherapyAgent → decoded procedure name
            (248, None),         # therapyReason
            (249, None),         # route
            (291, "PRONGO"),    # treatmentContinues → ongoing flag
        ]),
    ]),

    # PP — PK Parameters → StackedPkResults
    ("PP", 30, "local://BCSTUDY01/PP.csv", [
        (33, 1, [  # StackedPkResults
            (343, "STUDYID"),   # studyName
            (344, "STUDYID"),    # part
            (345, "USUBJID"),   # subject
            (361, "PPDTC"),     # visitDate
            (362, "VISITNUM"),  # visitNumber
            (985, "VISIT"),     # visit name
            (346, None),         # treatment
            (347, None),         # treatmentSchedule
            (348, "PPCAT"),     # treatmentCycle → PP category (e.g. cycle)
            (349, "PPTESTCD"), # parameter
            (350, "PPTEST"),    # analyte → full parameter name
            (351, "PPSTRESN"), # parameterValue
            (352, "PPSTRESU"), # parameterValueUnit
            (353, None),         # protocolSchedule
            (354, None),         # protocolScheduleStartDay
            (355, None),         # protocolScheduleStartHour
            (356, None),         # protocolScheduleStartMinute
            (363, None),         # protocolScheduleEnd
            (358, None),         # protocolScheduleEndDay
            (359, None),         # protocolScheduleEndHour
            (360, None),         # protocolScheduleEndMinute
            (357, None),         # comment
            (986, None),         # actualDose
        ]),
    ]),

    # BS — Biospecimen → SpecimenCollection
    ("BS", 28, "local://BCSTUDY01/BS.csv", [
        (31, 1, [  # SpecimenCollection (process_order=2 in DB but it's the only entity)
            (324, "STUDYID"),   # studyName
            (313, "STUDYID"),    # part
            (314, "USUBJID"),   # subject
            (315, "VISITNUM"),  # visitNumber
            (316, None),         # visitDate
            (325, "BSREFID"),   # spcIdentifier
            (317, "BSDTC"),     # spcDate → collection date
            (318, "BSCAT"),     # spcCategory → specimen category
            (319, None),         # protocolSchedule
            (320, "BSNOMDY"),   # protocolScheduleDay → nominal day
            (321, "BSNOMHR"),   # protocolScheduleHour → nominal hour
            (322, "BSNOMMIN"),  # protocolScheduleMinute → nominal minute
            (323, None),         # drugAdmDate
        ]),
    ]),

    # GE — Genetics → Biomarker
    ("GE", 62, "local://BCSTUDY01/GE.csv", [
        (67, 1, [  # Biomarker
            (930, "STUDYID"),   # studyName
            (931, "STUDYID"),    # part
            (932, "USUBJID"),   # subject
            (933, None),         # sampleType
            (934, None),         # sampleId
            (935, None),         # variantCount
            (936, None),         # cDNAChange
            (937, "GESOMSTAT"), # somaticStatus
            (938, None),         # aminoAcidChange
            (952, "GETESTCD"),  # gene → test code used as gene identifier
            (939, None),         # genomeLocation
            (940, None),         # externalVarianId
            (941, None),         # totalReads
            (942, None),         # germilineFreq
            (943, "GEVARTYP"),  # variantType
            (944, "GECAT"),     # mutationType → GE category
            (945, "GEVAL"),     # mutantAlleleFreq → genomic value
            (946, None),         # copyNumber
            (947, None),         # chromosomeInstabilityNumber
            (948, None),         # tumourMutationBurden
            (949, None),         # copyNumberAlterationType
            (950, None),         # rearrGene1
            (951, None),         # rearrDesc
        ]),
    ]),
]


def build_sql():
    insert_lines = ["BEGIN;"]

    # Insert file rules
    insert_lines.append("\n-- ===== FILE RULES =====")
    for domain_name, mfd_id, csv_file, entities in DOMAINS:
        fr_id = next_fr()
        insert_lines.append(
            f"INSERT INTO map_file_rule (mfr_id, mfr_name, mfr_enabled, mfr_is_updated, mfr_msr_id, mfr_mft_id)"
            f" VALUES ({fr_id}, '{csv_file}', 1, 1, {MSR_ID}, {MFT_ID}); -- {domain_name}"
        )

    # Insert map_description_file rows (links file rule to file description for checklist)
    insert_lines.append("\n-- ===== FILE DESCRIPTION LINKS (checklist) =====")
    file_rule_id_tmp = 124
    for domain_name, mfd_id, csv_file, entities in DOMAINS:
        insert_lines.append(
            f"INSERT INTO map_description_file (mdf_id, mdf_mfr_id, mdf_mfd_id)"
            f" VALUES ({file_rule_id_tmp}, {file_rule_id_tmp}, {mfd_id}); -- {domain_name}"
        )
        file_rule_id_tmp += 1

    # Reset so we can do mapping rules in domain order with correct file rule IDs
    file_rule_id = 124

    insert_lines.append("\n-- ===== MAPPING RULES + FIELD LINKS + COLUMN RULES =====")
    for domain_name, mfd_id, csv_file, entities in DOMAINS:
        insert_lines.append(f"\n-- {domain_name} (mfr_id={file_rule_id}, mfd_id={mfd_id})")
        for men_id, process_order, field_mappings in entities:
            insert_lines.append(f"  -- entity men_id={men_id} process_order={process_order}")
            for field in field_mappings:
                mfi_id  = field[0]
                csv_col = field[1]
                mmr_val = field[2] if len(field) > 2 else None
                mmr_id  = next_mmr()
                if mmr_val is not None:
                    insert_lines.append(
                        f"  INSERT INTO map_mapping_rule (mmr_id, mmr_mfr_id, mmr_maf_id, mmr_value)"
                        f" VALUES ({mmr_id}, {file_rule_id}, {MFR_AGG_FUN}, '{mmr_val}');"
                    )
                else:
                    insert_lines.append(
                        f"  INSERT INTO map_mapping_rule (mmr_id, mmr_mfr_id, mmr_maf_id)"
                        f" VALUES ({mmr_id}, {file_rule_id}, {MFR_AGG_FUN});"
                    )
                insert_lines.append(
                    f"  INSERT INTO map_mapping_rule_field (mrf_id, mrf_mmr_id, mrf_mfi_id)"
                    f" VALUES ({mmr_id}, {mmr_id}, {mfi_id});"
                )
                if csv_col is not None:
                    mcr_id = next_mcr()
                    insert_lines.append(
                        f"  INSERT INTO map_column_rule (mcr_id, mcr_mmr_id, mcr_name)"
                        f" VALUES ({mcr_id}, {mmr_id}, '{csv_col}');"
                    )
        file_rule_id += 1

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

    return "\n".join(insert_lines), "\n".join(setval_lines)


if __name__ == "__main__":
    sql, setval_sql = build_sql()

    # Write SQL to a file for inspection
    sql_path = "/tmp/bcstudy01_mappings.sql"
    with open(sql_path, "w") as f:
        f.write(sql)

    print(f"Generated {sql_path}")
    print(f"  File rules: {NEXT_FILE_RULE_ID[0] - 124} (IDs 124-{NEXT_FILE_RULE_ID[0]-1})")
    print(f"  Mapping rules: {NEXT_MMR_ID[0] - 2702} (IDs 2702-{NEXT_MMR_ID[0]-1})")
    print(f"  Column rules: {NEXT_MCR_ID[0] - 3016} (IDs 3016-{NEXT_MCR_ID[0]-1})")

    if "--dry-run" in sys.argv:
        print("\n--- SQL Preview (first 50 lines) ---")
        for line in sql.split("\n")[:50]:
            print(line)
        sys.exit(0)

    print("\nExecuting INSERT SQL as acuity user...")
    result = subprocess.run(
        ["docker", "exec", "-i", "acuity-docker-postgres-1",
         "psql", "-U", "acuity", "-d", "acuity_db"],
        input=sql, capture_output=True, text=True
    )
    if result.returncode == 0:
        successes = result.stdout.count("INSERT 0 1")
        print(f"SUCCESS — {successes} INSERT statements succeeded")
    else:
        print("FAILED:")
        print(result.stdout[-3000:])
        print(result.stderr[-1000:])
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
