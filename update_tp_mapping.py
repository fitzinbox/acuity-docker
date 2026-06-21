#!/usr/bin/env python3
"""
Update AdminUI DB column rules for TP.csv after pivot to wide format.

Changes (based on DB state: mfr_id=133 for TP, verified 2026-06-20):
  mmr 2845 (histologyType):      TPTESTCD → HIST
  mmr 2846 (histologyTypeDetails): TPTEST  → (none — no equivalent in wide format)
  mmr 2847 (tumourGrade):         (none)   → GRADE
  mmr 2848 (stage):               TPORRES  → (none — stage field dropped from mapping)
  mmr 2850 (primaryTumourStatus): (none)   → T
  mmr 2851 (nodesStatus):         (none)   → N
  mmr 2852 (metastasesStatus):    (none)   → M

SG mapping is unchanged — SGCAT/SGORRES columns are the same in the extended SG.csv.
"""

import subprocess
import sys

SQL = """
BEGIN;

-- histologyType: was TPTESTCD (long/thin test code), now HIST (wide column)
UPDATE map_column_rule SET mcr_name = 'HIST' WHERE mcr_mmr_id = 2845;

-- histologyTypeDetails: was TPTEST (full test name), no equivalent in wide format
DELETE FROM map_column_rule WHERE mcr_mmr_id = 2846;

-- stage: was TPORRES (generic result), dropped — stage is derivable from T/N/M
DELETE FROM map_column_rule WHERE mcr_mmr_id = 2848;

-- tumourGrade: new wide column GRADE (use nextval — acuity user cannot call setval)
INSERT INTO map_column_rule (mcr_id, mcr_mmr_id, mcr_name)
  VALUES (nextval('acuity.mcr_seq'), 2847, 'GRADE');

-- primaryTumourStatus: new wide column T
INSERT INTO map_column_rule (mcr_id, mcr_mmr_id, mcr_name)
  VALUES (nextval('acuity.mcr_seq'), 2850, 'T');

-- nodesStatus: new wide column N
INSERT INTO map_column_rule (mcr_id, mcr_mmr_id, mcr_name)
  VALUES (nextval('acuity.mcr_seq'), 2851, 'N');

-- metastasesStatus: new wide column M
INSERT INTO map_column_rule (mcr_id, mcr_mmr_id, mcr_name)
  VALUES (nextval('acuity.mcr_seq'), 2852, 'M');

COMMIT;
"""

if __name__ == '__main__':
    print("Updating TP AdminUI column rules...")
    if '--dry-run' in sys.argv:
        print(SQL)
        sys.exit(0)

    result = subprocess.run(
        ['docker', 'exec', '-i', 'acuity-docker-postgres-1',
         'psql', '-U', 'acuity', '-d', 'acuity_db'],
        input=SQL, capture_output=True, text=True
    )
    if result.returncode == 0:
        updates  = result.stdout.count('UPDATE')
        deletes  = result.stdout.count('DELETE')
        inserts  = result.stdout.count('INSERT')
        print(f"  OK — {updates} UPDATE, {deletes} DELETE, {inserts} INSERT")
        print(f"  stdout: {result.stdout.strip()}")
    else:
        print("FAILED:")
        print(result.stdout[-2000:])
        print(result.stderr[-500:])
        sys.exit(1)

    # Verify final state
    print("\nVerifying final TP column rules:")
    verify = subprocess.run(
        ['docker', 'exec', 'acuity-docker-postgres-1',
         'psql', '-U', 'acuity', '-d', 'acuity_db', '--set=search_path=acuity',
         '-c',
         'SELECT mmr.mmr_id, mrf.mrf_mfi_id, mcr.mcr_name '
         'FROM map_mapping_rule mmr '
         'JOIN map_mapping_rule_field mrf ON mrf.mrf_mmr_id = mmr.mmr_id '
         'LEFT JOIN map_column_rule mcr ON mcr.mcr_mmr_id = mmr.mmr_id '
         'WHERE mmr.mmr_mfr_id = 133 ORDER BY mmr.mmr_id;'],
        capture_output=True, text=True
    )
    print(verify.stdout)
