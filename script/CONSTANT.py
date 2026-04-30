import re
from anyio import Path

MODULE_CODE_RE = re.compile(r"\b([A-Z]{3,}\d{3}(?:_[A-Z0-9-]+)*)\b")
MODULE_ROOT_RE = re.compile(r"^([A-Z]{3,}\d{3})")

GROUP_PATTERNS = {
    r'^EPU-\d', r'^IDU-\d', r'^MECA-FISE-\d', r'^SNI-\d',
    r'^FISE\d', r'^FISA\d', r'^N3IE', r'^NTRANS', r'^E\d{4,}',
    r'^Scolarité', r'^examen_', r'^00000$', r'^\d{10,}$',
}
GROUP_RE = [re.compile(p, re.IGNORECASE) for p in GROUP_PATTERNS]

# All-uppercase multi-word pattern that matches "SURNAME FIRSTNAME" lines.
NAME_RE = re.compile(
    r'^[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝŸŒÆ]'
    r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝŸŒÆ\-]+'
    r'(?: [A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝŸŒÆ\-]+)+$'
)

DEFAULT_DATA_DIR     = Path(__file__).parent / "../data" / "json" / "ADE"
DEFAULT_VARIANTS_FILE = Path(__file__).parent / "../normalized_data" / "audit_variants.json"
OUTPUT_DATA_DIR = Path(__file__).parent / "../normalized_data"
DEFAULT_OUTPUT_FILE  = Path(__file__).parent / "../normalized_data" / "count_module_occurence.json"



TARGET_FILES = {"ADECal_IDU3.json", "ADECal_IDU4.json", "ADECal_IDU5.json"}
EXCLUDED_KEYS = {"description"}