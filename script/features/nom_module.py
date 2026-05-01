from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict


MODULE_CODE_RE = re.compile(r"\b([A-Z]{3,}\d{3}(?:_[A-Z0-9-]+)*)\b")
MODULE_ROOT_RE = re.compile(r"^([A-Z]{3,}\d{3})")
DEFAULT_DATA_DIR = Path(__file__).parent / "../data/json"
OUTPUT_DATA_DIR = Path(__file__).parent / "../normalized_data"


def extract_module_codes_from_text(text: str) -> set[str]:
    return {match.group(1) for match in MODULE_CODE_RE.finditer(text.upper())}


def module_root(code: str) -> str:
    match = MODULE_ROOT_RE.match(code)
    return match.group(1) if match else code


def module_suffix(code: str) -> str:
    """Return the part after the root (e.g. '_INGE_CM'), or '' if none."""
    root = module_root(code)
    return code[len(root):]


def safe_read_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"[WARN] Impossible de lire {path.name}: {exc}")
        return None


def walk_collect(obj, source: str, out: DefaultDict[str, set[str]]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_l = key.lower()
            if isinstance(value, str):
                if key_l in {"code_module", "module_precedent", "module_suivant", "title"}:
                    for code in extract_module_codes_from_text(value):
                        out[source].add(code)
                if key_l in {"description", "summary", "name", "nom"}:
                    for code in extract_module_codes_from_text(value):
                        out[source].add(code)
            walk_collect(value, source, out)
    elif isinstance(obj, list):
        for item in obj:
            walk_collect(item, source, out)


def build_official_codes(data_dir: Path, collected: dict[str, set[str]]) -> set[str]:
    official = set()
    for file_name in ("MAQUETTE_IDU.json", "Responsables_modules_IDU.json"):
        path = data_dir / file_name
        if path.exists():
            official.update(collected.get(file_name, set()))
    official.update(collected.get("dependance_sequence_IDU.json", set()))
    return official


def build_variants_by_root(all_codes: set[str]) -> dict[str, list[str]]:
    """
    Group all codes by their root (e.g. 'INFO633'), collecting every
    distinct suffix found (e.g. ['', '_IDU', '_INGE_CM', '_P01_G1']).
    Returns a dict sorted by root name, with suffixes sorted.
    """
    variants: DefaultDict[str, set[str]] = defaultdict(set)
    for code in all_codes:
        root = module_root(code)
        suffix = module_suffix(code)
        variants[root].add(suffix if suffix else "(racine)")
    return {root: sorted(suffixes) for root, suffixes in sorted(variants.items())}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vérifie la cohérence des noms/codes de modules à travers les fichiers JSON.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Dossier contenant les fichiers JSON (défaut: ./data/json)",
    )
    args = parser.parse_args()

    data_dir = args.data_dir
    if not data_dir.exists() or not data_dir.is_dir():
        print(f"[ERREUR] Dossier introuvable: {data_dir}")
        return 1

    # Only scan files starting with "ADECal"
    json_files = sorted(data_dir.glob("ADECal*.json"))
    if not json_files:
        print(f"[ERREUR] Aucun fichier ADECal*.json trouvé dans: {data_dir}")
        return 1

    print(f"Fichiers analysés : {[f.name for f in json_files]}")
    print()

    collected: DefaultDict[str, set[str]] = defaultdict(set)
    for json_path in json_files:
        payload = safe_read_json(json_path)
        if payload is None:
            continue
        walk_collect(payload, json_path.name, collected)

    # Official codes still loaded from the reference files (not from ADECal)
    all_reference_collected: DefaultDict[str, set[str]] = defaultdict(set)
    for ref_file in ("MAQUETTE_IDU.json", "Responsables_modules_IDU.json", "dependance_sequence_IDU.json"):
        ref_path = data_dir / ref_file
        if ref_path.exists():
            payload = safe_read_json(ref_path)
            if payload:
                walk_collect(payload, ref_file, all_reference_collected)

    official_codes = build_official_codes(data_dir, all_reference_collected)
    if not official_codes:
        print("[ERREUR] Aucun code module officiel trouvé.")
        return 1

    # Collect ALL codes across the ADECal files only
    all_codes: set[str] = set()
    for codes in collected.values():
        all_codes.update(codes)

    # --- Report: group by module root, list all suffixes ---
    print("=== Variantes par module ===")
    print(f"Dossier : {data_dir}")
    print(f"Codes officiels détectés : {len(official_codes)}")
    print(f"Codes totaux détectés    : {len(all_codes)}")
    print()

    variants = build_variants_by_root(all_codes)

    # --- Export variants to JSON ---
    OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_json_path = OUTPUT_DATA_DIR / "audit_variants.json"
    json_output = [
        {
            "racine": root,
            "variantes": suffixes,
        }
        for root, suffixes in variants.items()
    ]
    with output_json_path.open("w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    print(f"Fichier JSON exporté : {output_json_path}")
    print()

    for root, suffixes in variants.items():
        is_official = root in official_codes or any(
            f"{root}{s.replace('(racine)', '')}" in official_codes for s in suffixes
        )
        flag = "✓" if is_official else "?"
        print(f"[{flag}] {root}  ({len(suffixes)} variante(s))")
        for suffix in suffixes:
            full_code = root if suffix == "(racine)" else f"{root}{suffix}"
            marker = " [officiel]" if full_code in official_codes else ""
            print(f"      {suffix}{marker}")
        print()


if __name__ == "__main__":
    raise SystemExit(main())