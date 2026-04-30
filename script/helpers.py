"""
helpers.py
==========
Shared utility functions used across the IDU calendar analysis scripts.

Sections:
  1. ICS parsing          – unfold, parse_dt, extract_teachers, parse_ics_file, load_all_ics
  2. Name normalisation   – is_group_code, normalize_name, extract_teachers
  3. Module codes         – module_root, module_suffix, extract_codes,
                            extract_module_codes_from_text, summary_matches_module
  4. JSON helpers         – safe_read_json, load_responsables
  5. Conflict detection   – find_conflicts
  6. Preprocess / typing  – detect_type, detect_group, preprocess_data (pandas)
  7. Volume horaire       – get_type_cours, get_duree_heures, normaliser_titre,
                            verif_seance_module, verif_seance_all_modules,
                            verif_volume_horaire, proportion_module_present
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import DefaultDict

# ---------------------------------------------------------------------------
# 1 & 2 – Name normalisation + ICS description parsing
# ---------------------------------------------------------------------------

# Patterns that look like person names but are actually group / admin codes.
_GROUP_PATTERNS = {
    r'^EPU-\d', r'^IDU-\d', r'^MECA-FISE-\d', r'^SNI-\d',
    r'^FISE\d', r'^FISA\d', r'^N3IE', r'^NTRANS', r'^E\d{4,}',
    r'^Scolarité', r'^examen_', r'^00000$', r'^\d{10,}$',
}
_GROUP_RE = [re.compile(p, re.IGNORECASE) for p in _GROUP_PATTERNS]

# All-uppercase multi-word pattern that matches "SURNAME FIRSTNAME" lines.
_NAME_RE = re.compile(
    r'^[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝŸŒÆ]'
    r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝŸŒÆ\-]+'
    r'(?: [A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝŸŒÆ\-]+)+$'
)


def is_group_code(line: str) -> bool:
    """Return True if *line* is a group / admin code rather than a person name."""
    return any(p.search(line) for p in _GROUP_RE)


def normalize_name(raw: str) -> str:
    """Title-case a 'SURNAME FIRSTNAME' style string → 'Surname Firstname'."""
    return " ".join(w.capitalize() for w in raw.strip().split())


def extract_teachers(description: str) -> list[str]:
    """
    Parse a DESCRIPTION field (already unfolded) and return normalized
    instructor names found in it.  Falls back to ['(no instructor)'].
    """
    text = description.replace("\\n", "\n").replace("\\,", ",")
    names: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.search(r'exporté', line, re.IGNORECASE):
            continue
        if re.search(r'[,;\\]', line):
            continue
        if re.match(r'^\(.*\)$', line):        # (TD), (CM), (REUNION) …
            continue
        if is_group_code(line):
            continue
        if _NAME_RE.match(line):
            names.append(normalize_name(line))
    return names if names else ["(no instructor)"]


def responsible_in_teachers(resp: dict, teachers: list[str]) -> bool:
    """
    Return True if the responsible's name (from a Responsables JSON entry)
    appears in *teachers* – tries both 'Nom Prenom' and 'Prenom Nom' orders.
    """
    nom    = resp["nom"].strip().capitalize()
    prenom = resp["prenom"].strip().capitalize()
    return f"{nom} {prenom}" in teachers or f"{prenom} {nom}" in teachers


# ---------------------------------------------------------------------------
# 1 – ICS parsing
# ---------------------------------------------------------------------------

def unfold(raw: str) -> str:
    """Unfold RFC 5545 line-folding (CRLF/LF + leading whitespace → '')."""
    return re.sub(r'\r?\n[ \t]', '', raw)


def parse_dt(value: str) -> datetime:
    """Parse a DTSTART/DTEND value string to a UTC-aware datetime."""
    value = value.split(';')[-1].replace('Z', '').strip()
    fmt = '%Y%m%dT%H%M%S' if 'T' in value else '%Y%m%d'
    return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)


def parse_ics_file(path: Path) -> list[dict]:
    """
    Parse one ICS file and return a list of event dicts with keys:
    start, end, summary, description, teachers, location, uid, source_file.
    """
    raw = unfold(path.read_text(encoding='utf-8', errors='replace'))
    events: list[dict] = []

    for block in raw.split('BEGIN:VEVENT')[1:]:
        end_idx = block.find('END:VEVENT')
        if end_idx != -1:
            block = block[:end_idx]

        def _get(key: str) -> str:
            m = re.search(rf'^{key}[^:]*:(.+)$', block, re.MULTILINE)
            return m.group(1).strip() if m else ''

        dtstart, dtend = _get('DTSTART'), _get('DTEND')
        if not dtstart or not dtend:
            continue
        try:
            start, end = parse_dt(dtstart), parse_dt(dtend)
        except ValueError:
            continue

        description = _get('DESCRIPTION')
        events.append({
            'start':       start,
            'end':         end,
            'summary':     _get('SUMMARY') or '(no title)',
            'description': description,
            'teachers':    extract_teachers(description),
            'location':    _get('LOCATION'),
            'uid':         _get('UID'),
            'source_file': path.name,
        })
    return events


def load_all_ics(folder: Path, glob: str = '*.ics') -> list[dict]:
    """
    Load every ICS file matching *glob* in *folder*.
    Prints a summary line per file to stdout.
    """
    all_events: list[dict] = []
    ics_files = sorted(folder.glob(glob))
    if not ics_files:
        print(f"[warning] No files matching '{glob}' found in {folder}", file=sys.stderr)
    for f in ics_files:
        try:
            evts = parse_ics_file(f)
            print(f"  {f.name}: {len(evts)} events")
            all_events.extend(evts)
        except Exception as exc:
            print(f"  [error] {f.name}: {exc}", file=sys.stderr)
    return all_events


# ---------------------------------------------------------------------------
# 3 – Module code helpers
# ---------------------------------------------------------------------------

_MODULE_CODE_RE = re.compile(r"\b([A-Z]{3,}\d{3}(?:_[A-Z0-9-]+)*)\b")
_MODULE_ROOT_RE = re.compile(r"^([A-Z]{3,}\d{3})", re.IGNORECASE)


def module_root(code: str) -> str:
    """'INFO631_IDU' → 'INFO631'."""
    m = _MODULE_ROOT_RE.match(code.upper())
    return m.group(1) if m else code.upper()


def module_suffix(code: str) -> str:
    """'INFO631_INGE_CM' → '_INGE_CM' ; 'INFO631' → ''."""
    root = module_root(code)
    return code[len(root):]


def extract_codes(text: str) -> list[str]:
    """Return every module code found in *text* (duplicates included)."""
    return [m.group(1) for m in _MODULE_CODE_RE.finditer(text.upper())]


def extract_module_codes_from_text(text: str) -> set[str]:
    """Return the *set* of module codes found in *text*."""
    return {m.group(1) for m in _MODULE_CODE_RE.finditer(text.upper())}


def summary_matches_module(summary: str, root_code: str) -> bool:
    """Return True if the event SUMMARY contains *root_code* (case-insensitive)."""
    return root_code.upper() in summary.upper()


def build_variants_by_root(all_codes: set[str]) -> dict[str, list[str]]:
    """
    Group codes by their root, collecting every distinct suffix.
    '(racine)' is used when a code has no suffix.
    Returns a dict sorted by root, with suffixes sorted.
    """
    variants: DefaultDict[str, set[str]] = defaultdict(set)
    for code in all_codes:
        root   = module_root(code)
        suffix = module_suffix(code)
        variants[root].add(suffix if suffix else "(racine)")
    return {r: sorted(s) for r, s in sorted(variants.items())}


# ---------------------------------------------------------------------------
# 4 – JSON helpers
# ---------------------------------------------------------------------------

def safe_read_json(path: Path):
    """Load a JSON file, printing a warning and returning None on failure."""
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[WARN] Cannot read {path.name}: {exc}")
        return None


def load_responsables(path: Path) -> list[dict]:
    """
    Parse Responsables_modules_IDU.json and return the flat data list:
    [{'code_module': ..., 'nom': ..., 'prenom': ...}, ...]
    """
    raw = json.loads(path.read_text(encoding='utf-8'))
    for entry in raw:
        if entry.get('type') == 'table' and 'data' in entry:
            return entry['data']
    raise ValueError(f"No table data found in {path}")


def walk_collect(obj, source: str, out: DefaultDict[str, set[str]]) -> None:
    """
    Recursively walk a JSON object, extracting module codes from fields
    commonly used in the IDU data files (summary, description, code_module …).
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_l = key.lower()
            if isinstance(value, str) and key_l in {
                "code_module", "module_precedent", "module_suivant",
                "title", "description", "summary", "name", "nom",
            }:
                for code in extract_module_codes_from_text(value):
                    out[source].add(code)
            walk_collect(value, source, out)
    elif isinstance(obj, list):
        for item in obj:
            walk_collect(item, source, out)


def walk_count(obj, counter: DefaultDict[str, int], excluded_keys: set[str] | None = None) -> None:
    """
    Recursively walk a JSON object and count every module code occurrence,
    skipping keys listed in *excluded_keys* (default: {'description'}).
    """
    if excluded_keys is None:
        excluded_keys = {"description"}
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str) and key.lower() not in excluded_keys:
                for code in extract_codes(value):
                    counter[code] += 1
            walk_count(value, counter, excluded_keys)
    elif isinstance(obj, list):
        for item in obj:
            walk_count(item, counter, excluded_keys)


# ---------------------------------------------------------------------------
# 5 – Conflict detection
# ---------------------------------------------------------------------------

def find_conflicts(events: list[dict], verbose: bool = True) -> set[int]:
    """
    Return the set of event indices involved in scheduling conflicts
    (same teacher, overlapping time slots).  When *verbose* is True,
    print each conflict to stdout.
    """
    conflicts: set[int] = set()
    for i, a in enumerate(events):
        for j, b in enumerate(events):
            if j <= i:
                continue
            shared = set(a['teachers']) & set(b['teachers']) - {'(no instructor)'}
            if shared and a['start'] < b['end'] and b['start'] < a['end']:
                conflicts.add(i)
                conflicts.add(j)
                if verbose:
                    d1 = f"{a['start'].strftime('%Y-%m-%d %H:%M')} → {a['end'].strftime('%H:%M')}"
                    d2 = f"{b['start'].strftime('%Y-%m-%d %H:%M')} → {b['end'].strftime('%H:%M')}"
                    for teacher in shared:
                        print(f"\n⚠ OVERLAP for {teacher}:")
                        print(f"   [{d1}] {a['summary']}  (file: {a['source_file']})")
                        print(f"   [{d2}] {b['summary']}  (file: {b['source_file']})")
                        print("-" * 60)
    return conflicts


# ---------------------------------------------------------------------------
# 6 – Preprocess / typing  (requires pandas)
# ---------------------------------------------------------------------------

def detect_type(row: dict) -> str | None:
    """
    Infer session type (CM / TD / TP) from the Title + Description fields.
    Designed to work as a pandas .apply() callback.
    """
    text = (row.get('Title', '') + ' ' + row.get('Description', '')).upper()

    def _match(pattern: str) -> bool:
        return bool(re.search(r'(\b|_)' + pattern + r'(\b|_)', text))

    if _match('EXAMEN'):
        return 'CM'
    if _match('CM'):
        return 'CM'
    if _match('TD'):
        return 'TD'
    if _match('TP'):
        return 'TP'
    return None


def detect_group(row: dict) -> str | None:
    """
    Extract the TP group identifier (e.g. 'G1', 'G2') from Description.
    Designed to work as a pandas .apply() callback.
    """
    description = row.get('Description', '').upper()
    match = re.search(r'IDU-[345]-([A-Z]+\d?)', description)
    return match.group(1) if match else None


def preprocess_data(df):
    """
    Enrich a DataFrame loaded from an ADECal JSON file with:
    - Duration  (timedelta)
    - Code      (module root code extracted from Title)
    - Type      (CM / TD / TP, for rows that have a Code)
    - Group     (TP group, for TP rows)

    Requires pandas. Returns the mutated DataFrame.
    """
    import pandas as pd  # local import so helpers.py works without pandas too

    df['Duration'] = pd.to_datetime(df['Ends']) - pd.to_datetime(df['Starts'])
    df['Code']     = df['Title'].str.extract(r'([A-Za-z]{4}\d{3})', expand=False)

    with_code = df['Code'].notnull()
    df.loc[with_code, 'Type'] = df[with_code].apply(detect_type, axis=1)

    tp_mask = df['Type'] == 'TP'
    df.loc[tp_mask, 'Group'] = df[tp_mask].apply(detect_group, axis=1)

    return df


# ---------------------------------------------------------------------------
# 7 – Volume horaire verification
# ---------------------------------------------------------------------------

def get_type_cours(description: str) -> str | None:
    """Return the session type (CM / TD / TP) from the first line of Description."""
    first_line = description.split('\n')[0]
    for t in ('CM', 'TD', 'TP'):
        if f'({t})' in first_line:
            return t
    return None


def get_duree_heures(starts: str, ends: str) -> float:
    """Return the duration in hours between two ISO-format datetime strings."""
    t1 = datetime.fromisoformat(starts)
    t2 = datetime.fromisoformat(ends)
    return (t2 - t1).total_seconds() / 3600


def normaliser_titre(seance: dict) -> str | None:
    """Build a normalised title string 'CODE_TYPE' for deduplication."""
    if seance.get('code') is None:
        return None
    type_seance = seance.get('Type', seance.get('type'))
    return f"{seance['code']}_{type_seance}"


def verif_seance_module(ade: list[dict], nom_module: str) -> bool:
    """Return True if at least one session in *ade* belongs to *nom_module*."""
    for seance in ade:
        match = re.match(r'^[^_\s]+', seance['Title'])
        if match and match.group(0) == nom_module:
            return True
    return False


def verif_seance_all_modules(ade: list[dict], modules: list[str]) -> list[str]:
    """Return the list of modules from *modules* that have NO session in *ade*."""
    return [m for m in modules if not verif_seance_module(ade, m)]


def verif_volume_horaire(
    ade: list[dict],
    nom_module: str,
    volume_CM: float,
    volume_TD: float,
    volume_TP: float,
) -> str:
    """
    Check whether the scheduled hours for *nom_module* meet the expected
    volumes.  Returns 'OK' or a descriptive mismatch string.
    """
    count: dict[str, float] = {'CM': 0.0, 'TD': 0.0, 'TP': 0.0}
    seen: set = set()

    for seance in ade:
        if seance.get('code') != nom_module:
            continue
        type_seance = seance.get('type')
        if type_seance is None:
            continue

        date_jour   = seance['Starts'][:10]
        titre_norm  = normaliser_titre(seance)
        groupe      = seance.get('groupe', '')
        cle = (titre_norm, date_jour)

        if cle in seen:
            continue
        seen.add(cle)
        count[type_seance] += get_duree_heures(seance['Starts'], seance['Ends'])

    if count['CM'] >= volume_CM and count['TD'] >= volume_TD and count['TP'] >= volume_TP:
        return "OK"
    return (
        f"Volume horaire incorrect pour {nom_module} : "
        f"CM={count['CM']}h (attendu {volume_CM}h), "
        f"TD={count['TD']}h (attendu {volume_TD}h), "
        f"TP={count['TP']}h (attendu {volume_TP}h)"
    )


def proportion_module_present(ade: list[dict], modules: list[dict]) -> dict:
    """
    Compute the fraction of official modules that have at least one session
    in *ade*.  *modules* must be the raw parsed MAQUETTE_IDU.json list
    (the table entry with the 'data' key is extracted automatically).

    Returns a dict with keys: proportion, presents, absents, invalides.
    """
    # Accept either the raw wrapper list or the flat data list directly
    data: list[dict] = []
    if isinstance(modules, list):
        for entry in modules:
            if isinstance(entry, dict) and entry.get('type') == 'table' and 'data' in entry:
                data = entry['data']
                break
        if not data:
            # Assume it's already the flat list
            data = modules

    presents:  list[str] = []
    absents:   list[str] = []
    invalides: list[str] = []

    for module in data:
        code_brut = module.get('code_module', '')
        match     = re.match(r'^[^_\s]+', code_brut)
        if match:
            nom = match.group(0)
            (presents if verif_seance_module(ade, nom) else absents).append(nom)
        else:
            invalides.append(code_brut)

    total = len(presents) + len(absents)
    return {
        "proportion": len(presents) / total if total else 0.0,
        "presents":   presents,
        "absents":    absents,
        "invalides":  invalides,
    }