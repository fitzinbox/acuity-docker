#!/usr/bin/env python3
"""Generate 4 synthetic SDTM files for BCSTUDY01."""
import csv, os, random
from pathlib import Path

random.seed(42)
OUTPUT_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "local-file-storage/BCSTUDY01"
SUBJECTS = [f"BCSTUDY01-PT{i:03d}" for i in range(1, 101)]

# ── FA.csv ──────────────────────────────────────────────────────────────────
# Primary tumour location: all 100 subjects, BREAST
fa_rows = []
for i, subj in enumerate(SUBJECTS, 1):
    fa_rows.append({
        "STUDYID": "BCSTUDY01", "DOMAIN": "FA", "USUBJID": subj,
        "FASEQ": i, "FATESTCD": "PTUMLOC", "FATEST": "Primary Tumour Location",
        "FAORRES": "BREAST", "FASTRESC": "BREAST",
        "FALNKGRP": "AE", "FADTC": "2020-01-15",
    })
fa_path = OUTPUT_DIR / "FA.csv"
with open(fa_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(fa_rows[0].keys()))
    w.writeheader(); w.writerows(fa_rows)
print(f"Written {fa_path}  ({len(fa_rows)} rows)")

# ── CE.csv ──────────────────────────────────────────────────────────────────
# Clinical Events - Deaths derived from DS.csv
death_records = [
    ("BCSTUDY01-PT002", "2022-08-12"),
    ("BCSTUDY01-PT031", "2022-08-27"),
    ("BCSTUDY01-PT032", "2022-06-29"),
    ("BCSTUDY01-PT050", "2022-08-14"),
    ("BCSTUDY01-PT053", "2022-08-23"),
    ("BCSTUDY01-PT087", "2022-06-13"),
    ("BCSTUDY01-PT097", "2022-07-20"),
]
ce_rows = []
for seq, (subj, dtc) in enumerate(death_records, 1):
    ce_rows.append({
        "STUDYID": "BCSTUDY01", "DOMAIN": "CE", "USUBJID": subj,
        "CESEQ": seq, "CETERM": "DEATH", "CEDECOD": "DEATH",
        "CECAT": "DEATH", "CESTDTC": dtc, "CEENDTC": dtc,
        "CESEV": "FATAL",
    })
ce_path = OUTPUT_DIR / "CE.csv"
with open(ce_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(ce_rows[0].keys()))
    w.writeheader(); w.writerows(ce_rows)
print(f"Written {ce_path}  ({len(ce_rows)} rows)")

# ── PS.csv — Performance Status ──────────────────────────────────────────────
# ECOG PS 0-2 distribution: 20% PS0, 50% PS1, 30% PS2 (plausible for Phase 2 BC)
# 3 assessments per subject: baseline (day 1), cycle 2 (day 29), cycle 4 (day 85)
timepoints = [("2020-01-15", 1), ("2020-02-13", 2), ("2020-03-13", 4)]
ps_distribution = [0]*20 + [1]*50 + [2]*30  # 100 baseline PS values
random.shuffle(ps_distribution)

ps_rows = []
seq = 0
for subj_idx, subj in enumerate(SUBJECTS):
    baseline_ps = ps_distribution[subj_idx]
    for dtc, cycle in timepoints:
        # PS tends to worsen or stay same over time
        ps = min(2, baseline_ps + random.choices([0, 1], weights=[80, 20])[0])
        seq += 1
        ps_rows.append({
            "STUDYID": "BCSTUDY01", "DOMAIN": "PS", "USUBJID": subj,
            "PSSEQ": seq, "PSTESTCD": "ECOG", "PSTEST": "ECOG Performance Status",
            "PSORRES": str(ps), "PSSTRESC": str(ps), "PSSTRESN": ps,
            "PSDTC": dtc, "VISITNUM": cycle, "VISIT": f"CYCLE {cycle} DAY 1",
        })
ps_path = OUTPUT_DIR / "PS.csv"
with open(ps_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(ps_rows[0].keys()))
    w.writeheader(); w.writerows(ps_rows)
print(f"Written {ps_path}  ({len(ps_rows)} rows)")

# ── DE.csv — Disease Extent ──────────────────────────────────────────────────
# Breast cancer staging at baseline: Stage I 10%, II 35%, III 40%, IV 15%
# Staging per TNM: T, N, M status for each subject
staging = (
    ["I"]*10 + ["II"]*35 + ["III"]*40 + ["IV"]*15
)
random.shuffle(staging)

stage_to_metastatic = {"I": "N", "II": "N", "III": "Y", "IV": "Y"}
stage_to_nodes = {
    "I": "NEGATIVE", "II": "POSITIVE", "III": "POSITIVE", "IV": "POSITIVE"
}
stage_to_meta = {
    "I": "NONE", "II": "NONE", "III": "REGIONAL", "IV": "DISTANT"
}
stage_to_site = {
    "I": "LOCAL", "II": "LOCAL", "III": "LOCAL/REGIONAL", "IV": "METASTATIC"
}

de_rows = []
for i, (subj, stage) in enumerate(zip(SUBJECTS, staging), 1):
    de_rows.append({
        "STUDYID": "BCSTUDY01", "DOMAIN": "DE", "USUBJID": subj,
        "DESEQ": i,
        "DECAT": "BREAST CANCER",
        "DESTAGE": stage,
        "DEMETADV": stage_to_metastatic[stage],
        "DESITE": stage_to_site[stage],
        "DENODST": stage_to_nodes[stage],
        "DEMETAST": stage_to_meta[stage],
        "DEDTC": "2020-01-15",
    })
de_path = OUTPUT_DIR / "DE.csv"
with open(de_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(de_rows[0].keys()))
    w.writeheader(); w.writerows(de_rows)
print(f"Written {de_path}  ({len(de_rows)} rows)")

print("\nDone. Summary:")
print(f"  FA.csv: {len(fa_rows)} rows (primary tumour location, all BREAST)")
print(f"  CE.csv: {len(ce_rows)} rows (7 deaths from DS.csv)")
print(f"  PS.csv: {len(ps_rows)} rows (ECOG 0-2, 3 timepoints x 100 subjects)")
print(f"  DE.csv: {len(de_rows)} rows (staging I-IV, 100 subjects)")
