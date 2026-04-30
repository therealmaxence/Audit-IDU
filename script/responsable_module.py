#!/usr/bin/env python3
"""
responsable_presence.py

Cross-references Responsables_modules_IDU.json with ADECal*.ics files to count
how often the declared responsible (nom/prenom) appears in the DESCRIPTION of
events whose SUMMARY contains the matching module code.

Reuses the ICS-parsing helpers from person_unicity_ade.py.

Usage:
    python responsable_presence.py
    python responsable_presence.py --ics-dir path/to/ics --resp-file path/to/Responsables_modules_IDU.json
    python responsable_presence.py --output report.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from helpers import (
    load_all_ics,
    load_responsables,
    module_root,
    summary_matches_module,
    responsible_in_teachers,
)

# ---------------------------------------------------------------------------
# ICS parsing  (ported from person_unicity_ade.py)
# ---------------------------------------------------------------------------

GROUP_WORDS = {
    r'^EPU-\d', r'^IDU-\d', r'^MECA-FISE-\d', r'^SNI-\d', r'^FISE\d', r'^FISA\d',
    r'^N3IE', r'^NTRANS', r'^E\d{4,}', r'^Scolarité', r'^examen_', r'^00000$',
    r'^\d{10,}$',
}
GROUP_RE = [re.compile(p, re.IGNORECASE) for p in GROUP_WORDS]

NAME_RE = re.compile(
    r'^[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝŸŒÆ]'
    r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝŸŒÆ\-]+'
    r'(?: [A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝŸŒÆ\-]+)+$'
)

MODULE_ROOT_RE = re.compile(r'^([A-Z]{3,}\d{3})', re.IGNORECASE)


def is_group_code(line: str) -> bool:
    return any(p.search(line) for p in GROUP_RE)


def normalize_name(raw: str) -> str:
    return " ".join(w.capitalize() for w in raw.strip().split())


def extract_teachers(description: str) -> list[str]:
    text = description.replace("\\n", "\n").replace("\\,", ",")
    names = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.search(r'exporté', line, re.IGNORECASE):
            continue
        if re.search(r'[,;\\]', line):
            continue
        if re.match(r'^\(.*\)$', line):
            continue
        if is_group_code(line):
            continue
        if NAME_RE.match(line):
            names.append(normalize_name(line))
    return names if names else ["(no instructor)"]


def unfold(raw: str) -> str:
    return re.sub(r'\r?\n[ \t]', '', raw)


def parse_dt(value: str) -> datetime:
    value = value.split(';')[-1].replace('Z', '').strip()
    fmt = '%Y%m%dT%H%M%S' if 'T' in value else '%Y%m%d'
    return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)


def parse_ics_file(path: Path) -> list[dict]:
    raw = unfold(path.read_text(encoding='utf-8', errors='replace'))
    events = []
    for block in raw.split('BEGIN:VEVENT')[1:]:
        end_idx = block.find('END:VEVENT')
        if end_idx != -1:
            block = block[:end_idx]

        def get(key):
            m = re.search(rf'^{key}[^:]*:(.+)$', block, re.MULTILINE)
            return m.group(1).strip() if m else ''

        dtstart, dtend = get('DTSTART'), get('DTEND')
        if not dtstart or not dtend:
            continue
        try:
            start, end = parse_dt(dtstart), parse_dt(dtend)
        except ValueError:
            continue

        summary     = get('SUMMARY') or '(no title)'
        description = get('DESCRIPTION')
        uid         = get('UID')

        events.append({
            'start':       start,
            'end':         end,
            'summary':     summary,
            'description': description,
            'teachers':    extract_teachers(description),
            'uid':         uid,
            'source_file': path.name,
        })
    return events

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Count how often a module responsible appears in their own course ICS descriptions.'
    )
    parser.add_argument('--ics-dir',   default='data/ics', help='Folder with ADECal*.ics files (default: data/ics)')
    parser.add_argument('--resp-file', default='data/json/Responsables_modules_IDU.json', help='Path to Responsables_modules_IDU.json')
    parser.add_argument('--output',    default='normalized_data/occurence_responsables_modules.json', help='Optional JSON output path')
    args = parser.parse_args()

    ics_dir   = Path(args.ics_dir)
    resp_file = Path(args.resp_file)

    if not ics_dir.is_dir():
        sys.exit(f"[error] ICS directory not found: {ics_dir.resolve()}")
    if not resp_file.is_file():
        sys.exit(f"[error] Responsables file not found: {resp_file.resolve()}")

    # --- Load data ---
    print(f"Loading ICS files from: {ics_dir.resolve()}")
    events = load_all_ics(ics_dir)
    print(f"Total events loaded: {len(events)}\n")

    print(f"Loading responsables from: {resp_file.resolve()}")
    responsables = load_responsables(resp_file)
    print(f"Total responsables: {len(responsables)}\n")

    # --- Build per-module results ---
    results = []

    for resp in responsables:
        code     = resp['code_module']
        root     = module_root(code)
        nom      = resp['nom'].strip().capitalize()
        prenom   = resp['prenom'].strip().capitalize()
        full_name = f"{nom} {prenom}"

        matched_events     = [e for e in events if summary_matches_module(e['summary'], root)]
        present_events     = [e for e in matched_events if responsible_in_teachers(resp, e['teachers'])]
        absent_events      = [e for e in matched_events if not responsible_in_teachers(resp, e['teachers'])]

        results.append({
            'code_module':    code,
            'responsable':    full_name,
            'total_sessions': len(matched_events),
            'present':        len(present_events),
            'absent':         len(absent_events),
            'presence_rate':  round(len(present_events) / len(matched_events) * 100, 1) if matched_events else None,
            'present_events': [
                {'summary': e['summary'], 'start': e['start'].isoformat(), 'file': e['source_file']}
                for e in present_events
            ],
            'absent_events': [
                {
                    'summary':  e['summary'],
                    'start':    e['start'].isoformat(),
                    'file':     e['source_file'],
                    'teachers_found': e['teachers'],
                }
                for e in absent_events
            ],
        })

    # --- Console report ---
    print("=" * 70)
    print("RESPONSABLE PRESENCE IN ICS DESCRIPTIONS")
    print("=" * 70)

    # Group by responsable for a cleaner view
    by_person: dict[str, list] = defaultdict(list)
    for r in results:
        by_person[r['responsable']].append(r)

    grand_total_sessions = grand_present = 0

    for person in sorted(by_person):
        rows = by_person[person]
        total_s = sum(r['total_sessions'] for r in rows)
        total_p = sum(r['present'] for r in rows)
        rate = round(total_p / total_s * 100, 1) if total_s else None
        grand_total_sessions += total_s
        grand_present        += total_p

        rate_str = f"{rate}%" if rate is not None else "N/A"
        print(f"\n👤 {person}  —  {total_p}/{total_s} sessions ({rate_str} presence rate)")
        for r in rows:
            if r['total_sessions'] == 0:
                continue
            marker = "✓" if r['present'] > 0 else "✗"
            print(f"   [{marker}] {r['code_module']:<25}  "
                  f"present {r['present']}/{r['total_sessions']}  "
                  f"({r['presence_rate']}%)")
            # Show sessions where responsible is ABSENT (substitutes / others)
            for ev in r['absent_events']:
                others = [t for t in ev['teachers_found'] if t != '(no instructor)']
                others_str = ', '.join(others) if others else '—'
                print(f"        ↳ absent in: {ev['summary']} ({ev['start'][:10]})  "
                      f"[taught by: {others_str}]")

    print()
    print("=" * 70)
    overall_rate = round(grand_present / grand_total_sessions * 100, 1) if grand_total_sessions else 0
    print(f"OVERALL: {grand_present}/{grand_total_sessions} sessions "
          f"taught by declared responsible ({overall_rate}%)")
    print("=" * 70)

    # Modules with no matching ICS events
    no_events = [r for r in results if r['total_sessions'] == 0]
    if no_events:
        print(f"\n⚠  {len(no_events)} module(s) found in Responsables but with NO matching ICS events:")
        for r in no_events:
            print(f"   {r['code_module']} ({r['responsable']})")

    # --- Optional JSON export ---
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\nJSON report written to: {out.resolve()}")


if __name__ == '__main__':
    main()