#!/usr/bin/env python3
"""
ics_calendar.py
Reads all .ics files from data/ics/, parses events, extracts+normalizes
instructor names from DESCRIPTION fields, detects scheduling conflicts,
and outputs a self-contained HTML calendar (calendar.html).

Usage:
    python ics_calendar.py
    python ics_calendar.py --ics-dir path/to/ics --output my_calendar.html
"""

import os
import re
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
# ICS parsing
# ---------------------------------------------------------------------------

GROUP_WORDS = {
    # typical group codes found in DESCRIPTION lines
    r'^EPU-\d',r'^IDU-\d',r'^MECA-FISE-\d',r'^SNI-\d',r'^FISE\d',r'^FISA\d',
    r'^N3IE',r'^NTRANS',r'^E\d{4,}',r'^Scolarité',r'^examen_',r'^00000$',
    r'^\d{10,}$',
}

GROUP_RE = [re.compile(p, re.IGNORECASE) for p in GROUP_WORDS]

NAME_RE = re.compile(
    r'^[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝŸŒÆ]'   # starts uppercase
    r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝŸŒÆ\-]+'  # more uppercase / hyphen
    r'(?: [A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝŸŒÆ\-]+)+$'  # at least two words
)


def is_group_code(line: str) -> bool:
    for p in GROUP_RE:
        if p.search(line):
            return True
    return False


def normalize_name(raw: str) -> str:
    """Title-case a SURNAME FIRSTNAME style name."""
    return " ".join(w.capitalize() for w in raw.strip().split())


def extract_teachers(description: str) -> list[str]:
    """
    Parse the DESCRIPTION value (already unfolded) and return a list of
    normalized instructor names.  Returns ['(no instructor)'] when none found.
    """
    # ICS folded lines already unfolded by parse_ics; unescape \\n → newline
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
        if re.match(r'^\(.*\)$', line):   # e.g. (TD), (CM) …
            continue
        if is_group_code(line):
            continue
        if NAME_RE.match(line):
            names.append(normalize_name(line))
    return names if names else ["(no instructor)"]


def unfold(raw: str) -> str:
    """Unfold RFC 5545 line folding (CRLF + whitespace → nothing)."""
    return re.sub(r'\r?\n[ \t]', '', raw)


def parse_dt(value: str) -> datetime:
    """Parse DTSTART/DTEND value to UTC datetime."""
    value = value.split(';')[-1]  # strip VALUE=DATE-TIME etc.
    value = value.replace('Z', '').strip()
    fmt = '%Y%m%dT%H%M%S' if 'T' in value else '%Y%m%d'
    dt = datetime.strptime(value, fmt)
    return dt.replace(tzinfo=timezone.utc)


def parse_ics_file(path: Path) -> list[dict]:
    """Return list of event dicts from one ICS file."""
    raw = path.read_text(encoding='utf-8', errors='replace')
    raw = unfold(raw)

    events = []
    for block in raw.split('BEGIN:VEVENT')[1:]:
        end_idx = block.find('END:VEVENT')
        if end_idx != -1:
            block = block[:end_idx]

        def get(key):
            m = re.search(rf'^{key}[^:]*:(.+)$', block, re.MULTILINE)
            return m.group(1).strip() if m else ''

        dtstart = get('DTSTART')
        dtend   = get('DTEND')
        if not dtstart or not dtend:
            continue

        try:
            start = parse_dt(dtstart)
            end   = parse_dt(dtend)
        except ValueError:
            continue

        summary     = get('SUMMARY') or '(no title)'
        description = get('DESCRIPTION')
        location    = get('LOCATION')
        uid         = get('UID')
        source_file = path.name

        teachers = extract_teachers(description)

        events.append({
            'start':       start,
            'end':         end,
            'summary':     summary,
            'teachers':    teachers,
            'location':    location,
            'uid':         uid,
            'source_file': source_file,
        })

    return events


def load_all_ics(folder: Path) -> list[dict]:
    all_events = []
    ics_files = sorted(folder.glob('*.ics'))
    if not ics_files:
        print(f"[warning] No .ics files found in {folder}", file=sys.stderr)
    for f in ics_files:
        try:
            evts = parse_ics_file(f)
            print(f"  {f.name}: {len(evts)} events")
            all_events.extend(evts)
        except Exception as e:
            print(f"  [error] {f.name}: {e}", file=sys.stderr)
    return all_events


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def find_conflicts(events: list[dict]) -> set[int]:
    """
    Returns indices of events where two events share a teacher and overlap.
    Prints the exact details of the conflict to the console.
    """
    conflicts = set()
    for i, a in enumerate(events):
        for j, b in enumerate(events):
            if j <= i:
                continue
            
            shared = set(a['teachers']) & set(b['teachers']) - {'(no instructor)'}
            
            # If they share a teacher AND the times overlap
            if shared and a['start'] < b['end'] and b['start'] < a['end']:
                conflicts.add(i)
                conflicts.add(j)
                
                # Format dates nicely for printing
                d1_start = a['start'].strftime('%Y-%m-%d %H:%M')
                d1_end = a['end'].strftime('%H:%M')
                d2_start = b['start'].strftime('%Y-%m-%d %H:%M')
                d2_end = b['end'].strftime('%H:%M')
                
                for teacher in shared:
                    print(f"\n⚠ OVERLAP DETECTED for {teacher}:")
                    print(f"   Event 1: [{d1_start} to {d1_end}] {a['summary']} (File: {a['source_file']})")
                    print(f"   Event 2: [{d2_start} to {d2_end}] {b['summary']} (File: {b['source_file']})")
                    print("-" * 60)
                    
    return conflicts

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='ICS → HTML calendar by instructor')
    parser.add_argument('--ics-dir', default='data/ics', help='Folder with .ics files (default: data/ics)')
    parser.add_argument('--output',  default='calendar.html',  help='Output HTML file (default: calendar.html)')
    args = parser.parse_args()

    ics_dir = Path(args.ics_dir)
    if not ics_dir.is_dir():
        sys.exit(f"[error] Directory not found: {ics_dir}")

    print(f"Loading ICS files from: {ics_dir.resolve()}")
    events = load_all_ics(ics_dir)
    if not events:
        sys.exit("[error] No events found — nothing to render.")

    print(f"Total events: {len(events)}")


    conflicts = find_conflicts(events)
    if conflicts:
        print(f"⚠  Conflicts detected across {len(conflicts)} ")

if __name__ == '__main__':
    main()