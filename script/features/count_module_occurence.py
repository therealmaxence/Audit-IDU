from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

MODULE_CODE_RE = re.compile(r"\b([A-Z]{3,}\d{3}(?:_[A-Z0-9-]+)*)\b")

DEFAULT_DATA_DIR     = Path(__file__).parent / "../data" / "json"
DEFAULT_VARIANTS_FILE = Path(__file__).parent / "../normalized_data" / "audit_variants.json"
DEFAULT_OUTPUT_FILE  = Path(__file__).parent / "../normalized_data" / "count_module_occurence.json"

TARGET_FILES = {"ADECal_IDU3.json", "ADECal_IDU4.json", "ADECal_IDU5.json"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_codes(text: str) -> list[str]:
    """Return every module code found in a string (may contain duplicates)."""
    return [m.group(1) for m in MODULE_CODE_RE.finditer(text.upper())]


EXCLUDED_KEYS = {"description"}


def walk_count(obj, counter: defaultdict) -> None:
    """Recursively walk a JSON object and count every module code occurrence."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, str) and key.lower() not in EXCLUDED_KEYS:
                for code in extract_codes(value):
                    counter[code] += 1
            walk_count(value, counter)
    elif isinstance(obj, list):
        for item in obj:
            walk_count(item, counter)


def safe_read_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[WARN] Impossible de lire {path.name}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compte les occurrences de chaque module dans les fichiers ADECal."
    )
    parser.add_argument("--data-dir",      type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--variants-file", type=Path, default=DEFAULT_VARIANTS_FILE)
    parser.add_argument("--output-file",   type=Path, default=DEFAULT_OUTPUT_FILE)
    args = parser.parse_args()

    # --- Load variants ---
    variants_raw = safe_read_json(args.variants_file)
    if not variants_raw:
        print(f"[ERREUR] Impossible de charger : {args.variants_file}")
        return 1

    # Build lookup: variant_full_code -> racine
    # e.g. "INFO633_IDU" -> "INFO633",  "(racine)" means the root itself
    variant_to_root: dict[str, str] = {}
    roots: list[str] = []
    for entry in variants_raw:
        racine = entry["racine"]
        roots.append(racine)
        for suffix in entry["variantes"]:
            full = racine if suffix == "(racine)" else f"{racine}{suffix}"
            variant_to_root[full] = racine

    all_known_codes = set(variant_to_root.keys())

    # --- Count occurrences across target files ---
    global_counter: defaultdict[str, int] = defaultdict(int)

    for filename in sorted(TARGET_FILES):
        path = args.data_dir / filename
        if not path.exists():
            print(f"[WARN] Fichier introuvable : {path}")
            continue
        payload = safe_read_json(path)
        if payload is None:
            continue
        walk_count(payload, global_counter)
        print(f"[OK] Traité : {filename}")

    # --- Aggregate by racine ---
    # Only count codes that are in our known variants
    root_totals: defaultdict[str, int] = defaultdict(int)
    variant_counts: defaultdict[str, int] = defaultdict(int)

    for code, count in global_counter.items():
        if code in all_known_codes:
            racine = variant_to_root[code]
            root_totals[racine] += count
            variant_counts[code] += count

    # --- Build output structure ---
    output = []
    for entry in variants_raw:
        racine = entry["racine"]
        variants_detail = []
        for suffix in entry["variantes"]:
            full = racine if suffix == "(racine)" else f"{racine}{suffix}"
            count = variant_counts.get(full, 0)
            variants_detail.append({
                "code":     full,
                "suffixe":  suffix,
                "occurences": count,
            })
        output.append({
            "racine":        racine,
            "total_occurences": root_totals.get(racine, 0),
            "variantes":     variants_detail,
        })

    # --- Print report ---
    print()
    print("=== Occurrences par module ===")
    print()
    for entry in output:
        total = entry["total_occurences"]
        if total == 0:
            continue  # skip modules not present in the ADECal files
        print(f"  {entry['racine']}  —  total : {total}")
        for v in entry["variantes"]:
            if v["occurences"] > 0:
                print(f"    {v['code']:<45} {v['occurences']:>4} occurrence(s)")
        print()

    # --- Write JSON output ---
    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    with args.output_file.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Fichier JSON exporté : {args.output_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())