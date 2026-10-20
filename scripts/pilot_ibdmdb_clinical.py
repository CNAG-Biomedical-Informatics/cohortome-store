"""Read-only source audit and CSV preparation; no dataset replacement."""
import csv
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

def prepare(source, output):
    output.mkdir(parents=True, exist_ok=False)
    with source.open() as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    groups = defaultdict(list)
    for row in rows:
        groups[(row["Participant ID"], row["week_num"])].append(row)
    # Pilot retains separate source rows: never silently merge specimen rows.
    # Final snapshot grouping requires conflict review.
    with (output / "input.csv").open("w") as handle:
        writer = csv.DictWriter(handle, fieldnames=["pilot_record_id", *fields])
        writer.writeheader()
        for index, row in enumerate(rows):
            writer.writerow({"pilot_record_id": f"pilot-{index + 1}", **row})
    conflicts = Counter()
    for group in groups.values():
        for field in fields:
            values = {r[field] for r in group if r[field].strip()}
            if len(values) > 1:
                conflicts[field] += 1
    summary = {
        "source_rows": len(rows), "source_columns": len(fields),
        "participant_week_groups": len(groups),
        "groups_with_conflicting_nonempty_values_by_column": dict(conflicts),
        "purpose": "Mapping feasibility only; source rows not yet reconciled into snapshots",
    }
    (output / "source-audit.json").write_text(json.dumps(summary, indent=2))
    print({k: summary[k] for k in ("source_rows", "source_columns", "participant_week_groups")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.output)
