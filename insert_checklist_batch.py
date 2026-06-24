#!/usr/bin/env python3
"""Generate synthetic CSV files and insert AdminUI mappings for 16 net-new entities.

Exercises every remaining AdminUI Data Checklist item for BCSTUDY01.

Group 1 — Oncology/Clinical:
  ConmedProcedure (mfd_id=48) → PROCED.csv   (mfr_id=150)
  MedDosDisc      (mfd_id=11) → DD.csv       (mfr_id=151)
  Consent         (mfd_id=49) → IC.csv       (mfr_id=152)
  PatientData     (mfd_id=63) → QS.csv       (mfr_id=153)

Group 2 — Liver:
  LiverDI         (mfd_id=47) → LIVERDI.csv  (mfr_id=154)
  LiverSS         (mfd_id=55) → LIVERSS.csv  (mfr_id=155)
  LiverRF         (mfd_id=57) → LIVERRISK.csv(mfr_id=156)

Group 3 — Cardiac:
  DECG            (mfd_id=27) → DECG.csv     (mfr_id=157)  dual: Test + DECG
  LVEF            (mfd_id=8)  → LVEF.csv     (mfr_id=158)  dual: Test + LVEF

Group 4 — Disease-specific dummy:
  Exacerbation    (mfd_id=35) → EXA.csv      (mfr_id=159)
  ExaSeverityMap  (mfd_id=39) → EXASEV.csv   (mfr_id=160)
  LungFunction    (mfd_id=36) → LF.csv       (mfr_id=161)
  EDiary          (mfd_id=40) → EDIARY.csv   (mfr_id=162)
  CIEvent         (mfd_id=60) → CIE.csv      (mfr_id=163)
  CVOT            (mfd_id=59) → CVOT.csv     (mfr_id=164)
  Cerebrovascular (mfd_id=61) → CEREBRO.csv  (mfr_id=165)

Note on "Hospitalisations": not a standalone entity in ACUITY. Hospitalisation data is
captured via ConmedProcedure.hospitalDischargeDate (mfi_id=656), which is mapped here.

IDs assume current maxima: mfr=149, mdf=150, mmr=3075, mrf=3075, mcr=3312.
Run --dry-run to print SQL without executing. Run --csv-only to write CSVs only.
"""
import csv
import io
import os
import random
import subprocess
import sys
from datetime import date, timedelta

random.seed(42)

# ── constants ──────────────────────────────────────────────────────────────────
MSR_ID  = 2
MFT_ID  = 1
MAF_ID  = 1
STUDY   = "BCSTUDY01"
CSV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local-file-storage/BCSTUDY01")

SUBJECTS = [f"BCSTUDY01-PT{i:03d}" for i in range(1, 101)]

# Subjects with highest ALT in BCSTUDY01 lab data — clinically coherent for Liver entities.
LIVER_SUBJECTS = [
    "BCSTUDY01-PT013","BCSTUDY01-PT076","BCSTUDY01-PT057","BCSTUDY01-PT094",
    "BCSTUDY01-PT092","BCSTUDY01-PT058","BCSTUDY01-PT048","BCSTUDY01-PT017",
    "BCSTUDY01-PT034","BCSTUDY01-PT065",
]


def ds(dt): return dt.isoformat()  # YYYY-MM-DD


# ── CSV generators ─────────────────────────────────────────────────────────────

def gen_proced():
    """ConmedProcedure — 20 subjects, oncology surgical/imaging procedures."""
    procs = [
        "Tumour Biopsy","CT Chest/Abdomen/Pelvis","Bone Scan",
        "Port-a-cath Insertion","MRI Brain","Paracentesis",
    ]
    rows = []
    for i, subj in enumerate(SUBJECTS[:20]):
        start   = date(2022, 3, 1) + timedelta(days=i * 10)
        end_dt  = start + timedelta(days=random.randint(1, 5))
        proc    = procs[i % len(procs)]
        hosp_dt = ds(end_dt) if proc in ("Port-a-cath Insertion", "Paracentesis") else ""
        rows.append([STUDY, subj, ds(start), proc, ds(end_dt), hosp_dt])
    return (
        ["STUDYID", "USUBJID", "PRDTC", "PRTERM", "PRENDTC", "PRHOSPDT"],
        rows
    )


def gen_dd():
    """MedDosDisc — 15 subjects who discontinued investigational product."""
    reasons = [
        "Adverse Event","Progressive Disease","Patient Withdrawn Consent",
        "Protocol Deviation","Physician Decision",
    ]
    specs = [
        "Grade 3 hepatotoxicity","RECIST PD confirmed","Patient preference",
        "Non-compliance with protocol","Clinical deterioration",
    ]
    rows = []
    for i, subj in enumerate(SUBJECTS[80:95]):
        dt = date(2022, 6, 1) + timedelta(days=i * 15)
        rows.append([STUDY, subj, ds(dt), reasons[i % 5], specs[i % 5], "EXEMESTABIB"])
    return (
        ["STUDYID", "USUBJID", "DDDTC", "DDREASN", "DDSPEC", "DDDRGNM"],
        rows
    )


def gen_ic():
    """Informed Consent — all 100 subjects, pre-first-dose dates."""
    rows = []
    base = date(2021, 12, 1)
    for i, subj in enumerate(SUBJECTS):
        dt = base + timedelta(days=i * 2 + random.randint(0, 7))
        rows.append([STUDY, subj, ds(dt)])
    return (["STUDYID", "USUBJID", "ICDTC"], rows)


def gen_qs():
    """PatientData — 20 subjects x 3 assessments, EORTC QLQ-C30 Global Health."""
    visits = [
        (date(2022, 2, 1), "Baseline"),
        (date(2022, 5, 1), "Week 12"),
        (date(2022, 8, 1), "Week 24"),
    ]
    rows = []
    for subj in SUBJECTS[:20]:
        for base_dt, _ in visits:
            dt    = base_dt + timedelta(days=random.randint(-3, 3))
            score = round(random.uniform(30.0, 90.0), 1)
            rows.append([
                STUDY, subj,
                "EORTC QLQ-C30 Global Health Score",
                ds(dt), ds(dt),
                str(score), "score", "eDiary",
            ])
    return (
        ["STUDYID","USUBJID","QSTEST","QSDTC","QSRPTDTC","QSSTRESN","QSSTRESU","QSSTYPE"],
        rows
    )


def gen_liverdi():
    """LiverDI — 10 top-ALT subjects, 2 diagnostic investigations each."""
    items = [
        ("Abdominal Ultrasound",         "No acute pathology identified"),
        ("Hepatitis B Surface Antigen",  "Negative"),
        ("Hepatitis C Antibody",         "Negative"),
        ("DILI Causality Assessment",    "Possible drug-induced liver injury"),
    ]
    rows = []
    for i, subj in enumerate(LIVER_SUBJECTS):
        for j in range(2):
            item, result = items[(i * 2 + j) % len(items)]
            dt = date(2022, 5, 1) + timedelta(days=i * 12 + j * 7)
            rows.append([STUDY, subj, item, ds(dt), result])
    return (["STUDYID","USUBJID","LIDITM","LIDTC","LIDRSLT"], rows)


def gen_liverss():
    """LiverSS — 8 top-ALT subjects, liver signs/symptoms during treatment."""
    terms = ["Nausea","Fatigue","Abdominal Discomfort","Jaundice","Pruritus"]
    rows  = []
    for i, subj in enumerate(LIVER_SUBJECTS[:8]):
        start = date(2022, 4, 1) + timedelta(days=i * 14)
        end   = start + timedelta(days=random.randint(7, 21))
        rows.append([STUDY, subj, terms[i % len(terms)],
                     "During study treatment", ds(start), ds(end)])
        if i % 3 == 0:
            s2 = end + timedelta(days=5)
            e2 = s2 + timedelta(days=14)
            rows.append([STUDY, subj, "Fatigue", "Concurrent", ds(s2), ds(e2)])
    return (["STUDYID","USUBJID","LISSTERM","LISSOCCN","LISSSDTC","LISSENDTC"], rows)


def gen_liverrisk():
    """LiverRF — 8 top-ALT subjects, pre-existing liver risk factors."""
    factors = [
        "Alcohol consumption",
        "Obesity (BMI >30)",
        "Herbal supplement use",
        "Pre-existing hepatic steatosis",
    ]
    rows = []
    for i, subj in enumerate(LIVER_SUBJECTS[:8]):
        dt = date(2022, 1, 15)
        rows.append([STUDY, subj, factors[i % len(factors)], "Pre-existing", ds(dt)])
        if i % 4 == 0:
            rows.append([STUDY, subj, "Herbal supplement use", "At screening", ds(dt)])
    return (["STUDYID","USUBJID","LIRFTERM","LIRFOCCN","LIRFSTDTC"], rows)


def gen_decg():
    """DECG — 20 subjects x 2 visits x 3 measurements (QT, QTcF, RR)."""
    tests  = ["QT", "QTcF", "RR"]
    visits = [(1, date(2022, 2, 15)), (3, date(2022, 8, 15))]
    rows   = []
    for subj in SUBJECTS[:20]:
        for visit_num, base_dt in visits:
            dt = base_dt + timedelta(days=random.randint(-2, 2))
            for tc in tests:
                if tc == "QT":
                    val = str(round(random.uniform(340, 450)))
                elif tc == "QTcF":
                    val = str(round(random.uniform(380, 440)))
                else:
                    val = str(round(random.uniform(750, 1050)))
                rows.append([STUDY, subj, ds(dt), str(visit_num), tc, val])
    return (["STUDYID","USUBJID","EGDTC","VISITNUM","EGTESTCD","EGSTRESN"], rows)


def gen_lvef():
    """LVEF — 30 subjects x 2 echocardiogram assessments."""
    visits = [(1, date(2022, 2, 1)), (3, date(2022, 8, 1))]
    rows   = []
    for subj in SUBJECTS[:30]:
        for visit_num, base_dt in visits:
            dt = base_dt + timedelta(days=random.randint(-3, 3))
            lvef_pct = round(random.uniform(50, 70)) if random.random() > 0.1 else round(random.uniform(40, 49))
            rows.append([STUDY, subj, ds(dt), str(visit_num), str(lvef_pct)])
    return (["STUDYID","USUBJID","LVDTC","VISITNUM","LVPCT"], rows)


def gen_exa():
    """Exacerbation — 5 subjects, dummy respiratory exacerbation events."""
    rows = []
    for i, subj in enumerate(SUBJECTS[:5]):
        start  = date(2022, 4, 1) + timedelta(days=i * 30)
        end    = start + timedelta(days=random.randint(5, 14))
        hosp   = "Y" if i % 2 == 0 else "N"
        hs     = ds(start) if hosp == "Y" else ""
        he     = ds(end)   if hosp == "Y" else ""
        rows.append([STUDY, subj, ds(start), ds(end), hosp, hs, he])
    return (["STUDYID","USUBJID","EXASTDTC","EXAENDTC","EXHASP","EXAHSPSTDTC","EXAHSPENDTC"], rows)


def gen_exasev():
    """ExaSeverityMap — 3 study-level exacerbation severity classification rules."""
    rules = [
        ("Mild",     "N", "N", "N", "Y", "N", "N"),
        ("Moderate", "N", "Y", "N", "Y", "N", "N"),
        ("Severe",   "Y", "Y", "N", "Y", "Y", "Y"),
    ]
    rows = [[STUDY, cls, dep, sys_, ics, abio, hosp, emer]
            for cls, dep, sys_, ics, abio, hosp, emer in rules]
    return (["STUDYID","EXACLASS","DEPO","SYSC","ICSUSE","ABIO","HOSP","EMER"], rows)


def gen_lf():
    """LungFunction — 5 subjects x 2 visits, dummy spirometry values."""
    visits = [(1, "SCRN", date(2022, 2, 1)), (3, "C3D1", date(2022, 8, 1))]
    rows   = []
    for subj in SUBJECTS[:5]:
        for visit_num, proto, base_dt in visits:
            dt       = base_dt + timedelta(days=random.randint(-2, 2))
            fev1l    = round(random.uniform(1.8, 3.5), 2)
            fev1pct  = round(random.uniform(75.0, 105.0))
            rows.append([STUDY, subj, str(visit_num), ds(dt), proto,
                         str(fev1l), str(fev1pct)])
    return (["STUDYID","USUBJID","LFVISIT","LFASSDTC","LFPROTSCH","LFEV1L","LFEV1PCT"], rows)


def gen_ediary():
    """EDiary — 5 subjects x 5 days, dummy morning/evening PEF measurements."""
    rows = []
    base = date(2022, 3, 1)
    for subj in SUBJECTS[:5]:
        for day_off in range(5):
            dt       = base + timedelta(days=day_off)
            pef_morn = str(round(random.uniform(350, 500)))
            pef_eve  = str(round(random.uniform(330, 480)))
            rows.append([STUDY, subj, ds(dt), pef_morn, pef_eve])
    return (["STUDYID","USUBJID","EDASSDT","EDPEFMORN","EDPEFEVE"], rows)


def gen_cie():
    """CIEvent — 3 subjects, dummy cardiac ischaemic events (CVOT context)."""
    events = [
        ("Chest Pain",        "Unstable Angina"),
        ("ST Elevation",      "STEMI"),
        ("Elevated Troponin", "NSTEMI"),
    ]
    rows = []
    for i, (term, diag) in enumerate(events):
        dt = date(2022, 9, 1) + timedelta(days=i * 30)
        rows.append([STUDY, SUBJECTS[i], ds(dt), term, diag])
    return (["STUDYID","USUBJID","CIESTDTC","CIETERM","CIEDIAG"], rows)


def gen_cvot():
    """CVOT — 3 subjects, dummy cardiovascular outcome trial endpoint events."""
    events = [
        ("Myocardial Infarction", "Major Adverse Cardiovascular Event"),
        ("Cardiovascular Death",  "Major Adverse Cardiovascular Event"),
        ("Ischaemic Stroke",      "Major Adverse Cardiovascular Event"),
    ]
    rows = []
    for i, (term, cat1) in enumerate(events):
        dt = date(2022, 10, 1) + timedelta(days=i * 20)
        rows.append([STUDY, SUBJECTS[i], ds(dt), term, cat1])
    return (["STUDYID","USUBJID","CVOTSTDTC","CVOTERM","CVOTCAT1"], rows)


def gen_cerebro():
    """Cerebrovascular — 2 subjects, dummy cerebrovascular events."""
    events = [
        ("Transient Ischaemic Attack", "TIA"),
        ("Ischaemic Stroke",           "Ischaemic Stroke"),
    ]
    rows = []
    for i, (term, etype) in enumerate(events):
        dt = date(2022, 11, 1) + timedelta(days=i * 20)
        rows.append([STUDY, SUBJECTS[i], ds(dt), term, etype])
    return (["STUDYID","USUBJID","CBVSTDTC","CBVTERM","CBVTYPE"], rows)


# ── entity registry ────────────────────────────────────────────────────────────
# (mfr_id, mdf_id, mfd_id, csv_filename, generator, fields)
# fields: list of (mfi_id, csv_column, mmr_id, mcr_id)
#
# IDs assigned sequentially from current maxima:
#   mfr=149→150+, mdf=150→151+, mmr/mrf=3075→3076+, mcr=3312→3313+

ENTITIES = [
    # ── Group 1 ───────────────────────────────────────────────────────────────
    (150, 151, 48, "PROCED.csv", gen_proced, [
        (640, "STUDYID",  3076, 3313),   # ConmedProcedure.studyName
        (641, "STUDYID",  3077, 3314),   # ConmedProcedure.part
        (642, "USUBJID",  3078, 3315),   # ConmedProcedure.subject
        (643, "PRTERM",   3079, 3316),   # ConmedProcedure.value (procedure name)
        (648, "PRDTC",    3080, 3317),   # ConmedProcedure.startDate
        (656, "PRHOSPDT", 3081, 3318),   # ConmedProcedure.hospitalDischargeDate
    ]),
    (151, 152, 11, "DD.csv", gen_dd, [
        (84,  "STUDYID",  3082, 3319),   # MedDosDisc.studyName
        (83,  "STUDYID",  3083, 3320),   # MedDosDisc.part
        (82,  "USUBJID",  3084, 3321),   # MedDosDisc.subject
        (78,  "DDDTC",    3085, 3322),   # MedDosDisc.ipdcDate
        (79,  "DDREASN",  3086, 3323),   # MedDosDisc.ipdcReas
        (80,  "DDSPEC",   3087, 3324),   # MedDosDisc.ipdcSpec
        (81,  "DDDRGNM",  3088, 3325),   # MedDosDisc.drugName
    ]),
    (152, 153, 49, "IC.csv", gen_ic, [
        (657, "STUDYID",  3089, 3326),   # Consent.studyName
        (658, "STUDYID",  3090, 3327),   # Consent.part
        (659, "USUBJID",  3091, 3328),   # Consent.subject
        (660, "ICDTC",    3092, 3329),   # Consent.consentDate
    ]),
    (153, 154, 63, "QS.csv", gen_qs, [
        (969, "STUDYID",   3093, 3330),  # PatientData.studyName
        (961, "STUDYID",   3094, 3331),  # PatientData.part
        (957, "USUBJID",   3095, 3332),  # PatientData.subject
        (958, "QSTEST",    3096, 3333),  # PatientData.measurementName
        (959, "QSDTC",     3097, 3334),  # PatientData.measurementDate
        (960, "QSRPTDTC",  3098, 3335),  # PatientData.reportDate
        (962, "QSSTRESN",  3099, 3336),  # PatientData.value
        (963, "QSSTRESU",  3100, 3337),  # PatientData.unit
        (965, "QSSTYPE",   3101, 3338),  # PatientData.sourceType
    ]),
    # ── Group 2 ───────────────────────────────────────────────────────────────
    (154, 155, 47, "LIVERDI.csv", gen_liverdi, [
        (631, "STUDYID",  3102, 3339),   # LiverDI.studyName
        (632, "STUDYID",  3103, 3340),   # LiverDI.part
        (633, "USUBJID",  3104, 3341),   # LiverDI.subject
        (634, "LIDITM",   3105, 3342),   # LiverDI.value (investigation name)
        (635, "LIDTC",    3106, 3343),   # LiverDI.date
        (636, "LIDRSLT",  3107, 3344),   # LiverDI.results
    ]),
    (155, 156, 55, "LIVERSS.csv", gen_liverss, [
        (715, "STUDYID",   3108, 3345),  # LiverSS.studyName
        (716, "STUDYID",   3109, 3346),  # LiverSS.part
        (717, "USUBJID",   3110, 3347),  # LiverSS.subject
        (719, "LISSTERM",  3111, 3348),  # LiverSS.value (symptom)
        (720, "LISSOCCN",  3112, 3349),  # LiverSS.occurrence
        (721, "LISSSDTC",  3113, 3350),  # LiverSS.startDate
        (722, "LISSENDTC", 3114, 3351),  # LiverSS.stopDate
    ]),
    (156, 157, 57, "LIVERRISK.csv", gen_liverrisk, [
        (744, "STUDYID",   3115, 3352),  # LiverRiskFactors.studyName
        (745, "STUDYID",   3116, 3353),  # LiverRiskFactors.part
        (746, "USUBJID",   3117, 3354),  # LiverRiskFactors.subject
        (748, "LIRFTERM",  3118, 3355),  # LiverRiskFactors.liverRiskFactor
        (749, "LIRFOCCN",  3119, 3356),  # LiverRiskFactors.occurrence
        (752, "LIRFSTDTC", 3120, 3357),  # LiverRiskFactors.startDate
    ]),
    # ── Group 3 ───────────────────────────────────────────────────────────────
    # DECG: dual entity — Test (men_id=15) process_order=1 + DECG (men_id=30) process_order=2
    (157, 158, 27, "DECG.csv", gen_decg, [
        (133, "STUDYID",  3121, 3358),   # Test.studyName
        (132, "STUDYID",  3122, 3359),   # Test.part
        (131, "USUBJID",  3123, 3360),   # Test.subject
        (129, "VISITNUM", 3124, 3361),   # Test.visit
        (130, "EGDTC",    3125, 3362),   # Test.date
        (305, "STUDYID",  3126, 3363),   # DECG.studyName
        (306, "STUDYID",  3127, 3364),   # DECG.part
        (307, "USUBJID",  3128, 3365),   # DECG.subject
        (308, "EGDTC",    3129, 3366),   # DECG.date
        (309, "EGTESTCD", 3130, 3367),   # DECG.measurementLabel
        (310, "EGSTRESN", 3131, 3368),   # DECG.measurementValue
    ]),
    # LVEF: dual entity — Test (men_id=15) process_order=1 + LVEF (men_id=9) process_order=2
    (158, 159, 8, "LVEF.csv", gen_lvef, [
        (133, "STUDYID",  3132, 3369),   # Test.studyName
        (132, "STUDYID",  3133, 3370),   # Test.part
        (131, "USUBJID",  3134, 3371),   # Test.subject
        (129, "VISITNUM", 3135, 3372),   # Test.visit
        (130, "LVDTC",    3136, 3373),   # Test.date
        (75,  "STUDYID",  3137, 3374),   # LVEF.studyName
        (73,  "STUDYID",  3138, 3375),   # LVEF.part
        (72,  "USUBJID",  3139, 3376),   # LVEF.subject
        (74,  "LVDTC",    3140, 3377),   # LVEF.date
        (69,  "LVPCT",    3141, 3378),   # LVEF.lvef (integer %)
    ]),
    # ── Group 4 ───────────────────────────────────────────────────────────────
    (159, 160, 35, "EXA.csv", gen_exa, [
        (461, "STUDYID",     3142, 3379),  # Exacerbation.studyName
        (462, "STUDYID",     3143, 3380),  # Exacerbation.part
        (463, "USUBJID",     3144, 3381),  # Exacerbation.subject
        (464, "EXASTDTC",    3145, 3382),  # Exacerbation.exacStartDate
        (465, "EXAENDTC",    3146, 3383),  # Exacerbation.exacEndDate
        (480, "EXHASP",      3147, 3384),  # Exacerbation.hospit
        (481, "EXAHSPSTDTC", 3148, 3385),  # Exacerbation.hospitStartDate
        (482, "EXAHSPENDTC", 3149, 3386),  # Exacerbation.hospitEndDate
    ]),
    (160, 161, 39, "EXASEV.csv", gen_exasev, [
        (511, "STUDYID",  3150, 3387),   # ExaSeverityMap.studyName (only mandatory field)
        (504, "EXACLASS", 3151, 3388),   # ExaSeverityMap.excClass
        (505, "DEPO",     3152, 3389),   # ExaSeverityMap.depotGcs
        (506, "SYSC",     3153, 3390),   # ExaSeverityMap.syscortTrt
        (507, "ICSUSE",   3154, 3391),   # ExaSeverityMap.icsTrt
        (508, "ABIO",     3155, 3392),   # ExaSeverityMap.antibioticsTrt
        (509, "HOSP",     3156, 3393),   # ExaSeverityMap.hospit
        (510, "EMER",     3157, 3394),   # ExaSeverityMap.emerTrt
    ]),
    (161, 162, 36, "LF.csv", gen_lf, [
        (486, "STUDYID",   3158, 3395),  # LungFunction.studyName
        (487, "STUDYID",   3159, 3396),  # LungFunction.part
        (488, "USUBJID",   3160, 3397),  # LungFunction.subject
        (489, "LFVISIT",   3161, 3398),  # LungFunction.visit
        (491, "LFASSDTC",  3162, 3399),  # LungFunction.assessDate
        (492, "LFPROTSCH", 3163, 3400),  # LungFunction.protocolSchedule
        (493, "LFEV1L",    3164, 3401),  # LungFunction.fev1l
        (494, "LFEV1PCT",  3165, 3402),  # LungFunction.fev1perc
    ]),
    (162, 163, 40, "EDIARY.csv", gen_ediary, [
        (530, "STUDYID",   3166, 3403),  # EDiary.studyName
        (518, "STUDYID",   3167, 3404),  # EDiary.part
        (519, "USUBJID",   3168, 3405),  # EDiary.subject
        (520, "EDASSDT",   3169, 3406),  # EDiary.assessmentDate
        (524, "EDPEFMORN", 3170, 3407),  # EDiary.pefMorning
        (526, "EDPEFEVE",  3171, 3408),  # EDiary.pefEvening
    ]),
    (163, 164, 60, "CIE.csv", gen_cie, [
        (874, "STUDYID",  3172, 3409),   # CIEvent.studyName
        (875, "STUDYID",  3173, 3410),   # CIEvent.part
        (876, "USUBJID",  3174, 3411),   # CIEvent.subject
        (880, "CIESTDTC", 3175, 3412),   # CIEvent.startDate
        (882, "CIETERM",  3176, 3413),   # CIEvent.eventTerm
        (895, "CIEDIAG",  3177, 3414),   # CIEvent.finalDiagnosis
    ]),
    (164, 165, 59, "CVOT.csv", gen_cvot, [
        (861, "STUDYID",   3178, 3415),  # CVOT.studyName
        (862, "STUDYID",   3179, 3416),  # CVOT.part
        (863, "USUBJID",   3180, 3417),  # CVOT.subject
        (865, "CVOTSTDTC", 3181, 3418),  # CVOT.startDate
        (867, "CVOTERM",   3182, 3419),  # CVOT.term
        (868, "CVOTCAT1",  3183, 3420),  # CVOT.category1
    ]),
    (165, 166, 61, "CEREBRO.csv", gen_cerebro, [
        (902, "STUDYID",  3184, 3421),   # Cerebrovascular.studyName
        (903, "STUDYID",  3185, 3422),   # Cerebrovascular.part
        (904, "USUBJID",  3186, 3423),   # Cerebrovascular.subject
        (906, "CBVSTDTC", 3187, 3424),   # Cerebrovascular.startDate
        (908, "CBVTERM",  3188, 3425),   # Cerebrovascular.term
        (909, "CBVTYPE",  3189, 3426),   # Cerebrovascular.eventType
    ]),
]


# ── CSV writer ─────────────────────────────────────────────────────────────────

def write_csv(filename, headers, rows):
    path = os.path.join(CSV_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    return path, len(rows)


# ── SQL builder ────────────────────────────────────────────────────────────────

def build_entity_sql(mfr_id, mdf_id, mfd_id, csv_file, fields):
    mfr_name = f"local://BCSTUDY01/{csv_file}"
    lines = [
        f"-- === {csv_file} (mfd_id={mfd_id}) ===",
        f"INSERT INTO map_file_rule (mfr_id,mfr_name,mfr_enabled,mfr_is_updated,mfr_msr_id,mfr_mft_id)"
        f" VALUES ({mfr_id},'{mfr_name}',1,1,{MSR_ID},{MFT_ID});",
        f"INSERT INTO map_description_file (mdf_id,mdf_mfr_id,mdf_mfd_id)"
        f" VALUES ({mdf_id},{mfr_id},{mfd_id});",
    ]
    for mfi_id, col, mmr_id, mcr_id in fields:
        lines += [
            f"INSERT INTO map_mapping_rule (mmr_id,mmr_mfr_id,mmr_maf_id) VALUES ({mmr_id},{mfr_id},{MAF_ID});",
            f"INSERT INTO map_mapping_rule_field (mrf_id,mrf_mmr_id,mrf_mfi_id) VALUES ({mmr_id},{mmr_id},{mfi_id});",
            f"INSERT INTO map_column_rule (mcr_id,mcr_mmr_id,mcr_name) VALUES ({mcr_id},{mmr_id},'{col}');",
        ]
    return "\n".join(lines)


def build_full_sql():
    parts = ["SET search_path TO acuity;", "BEGIN;", ""]
    for mfr_id, mdf_id, mfd_id, csv_file, _gen, fields in ENTITIES:
        parts.append(build_entity_sql(mfr_id, mdf_id, mfd_id, csv_file, fields))
        parts.append("")
    parts.append("COMMIT;")
    return "\n".join(parts)


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
        input=sql, capture_output=True, text=True,
    )


def verify_sql():
    checks = []
    for mfr_id, mdf_id, mfd_id, csv_file, _gen, fields in ENTITIES:
        n_fields = len(fields)
        checks.append(
            f"SELECT '{csv_file}' AS file, COUNT(*) AS mmr_count"
            f" FROM map_mapping_rule WHERE mmr_mfr_id={mfr_id};"
        )
    return "SET search_path TO acuity;\n" + "\n".join(checks)


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    dry_run  = "--dry-run"  in sys.argv
    csv_only = "--csv-only" in sys.argv

    print("=== Generating CSV files ===")
    total_rows = 0
    for mfr_id, mdf_id, mfd_id, csv_file, gen_fn, fields in ENTITIES:
        headers, rows = gen_fn()
        path, n = write_csv(csv_file, headers, rows)
        print(f"  {csv_file:20s}  {n:4d} rows → {path}")
        total_rows += n
    print(f"  Total: {total_rows} rows across {len(ENTITIES)} files\n")

    if csv_only:
        print("--csv-only: skipping DB inserts.")
        return

    sql = build_full_sql()

    if dry_run:
        print("=== SQL (dry run) ===")
        print(sql)
        return

    print("=== Inserting DB mappings ===")
    r = run_psql("acuity", sql)
    expected_inserts = sum(2 + 3 * len(fields) for _, _, _, _, _, fields in ENTITIES)
    actual_inserts   = r.stdout.count("INSERT 0 1")
    print(f"  Return code: {r.returncode} — {actual_inserts}/{expected_inserts} inserts")
    if r.returncode != 0 or actual_inserts < expected_inserts:
        print("STDOUT:", r.stdout[-3000:])
        print("STDERR:", r.stderr[-500:])
        sys.exit(1)

    print("  Advancing sequences...")
    sv = run_psql("dbadmin", SETVAL_SQL)
    if sv.returncode != 0:
        print("  setval FAILED:", sv.stderr[-500:])
        sys.exit(1)
    print("  Sequences advanced OK")

    print("\n=== Verifying field counts ===")
    v = run_psql("acuity", verify_sql())
    print(v.stdout)

    expected = {csv_file: len(fields) for _, _, _, csv_file, _, fields in ENTITIES}
    ok = True
    for mfr_id, mdf_id, mfd_id, csv_file, _, fields in ENTITIES:
        if v.returncode != 0:
            ok = False
    if ok:
        print("All mappings inserted successfully.\n")
        print("Next: trigger ETL → POST http://localhost:8001/scheduler/trigger")
        print("      with projectName=BCPROGRAMME&studyCode=BCSTUDY01")


if __name__ == "__main__":
    main()
