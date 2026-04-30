import pandas as pd
import re
from helpers import preprocess_data, save_data, load_data, detect_group, detect_type

def verif_seance_module(ade, nom_module):
    for seance in ade:
        match = re.match(r'^[^_\s]+', seance['Title'])
        if match and match.group(0) == nom_module:
            return True
    return False


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

if __name__ == "__main__":
    # Tests
    IDU3_data = load_data('data/json/ADECal_IDU3.json')
    preprocess_data(IDU3_data)
    print(IDU3_data.head(), IDU3_data.tail())

    IDU4_data = load_data('data/json/ADECal_IDU4.json')
    preprocess_data(IDU4_data)
    print(IDU4_data.head(), IDU4_data.tail())

    IDU5_data = load_data('data/json/ADECal_IDU5.json')
    preprocess_data(IDU5_data)
    print(IDU5_data.head(), IDU5_data.tail())

    print(IDU3_data[IDU3_data['Type'] == 'TP']['Group'].isnull().sum())
    print(IDU4_data[IDU4_data['Type'] == 'TP']['Group'].isnull().sum())
    print(IDU5_data[IDU5_data['Type'] == 'TP']['Group'].isnull().sum())

    print(IDU3_data[(IDU3_data['Type'] == 'TP') & (IDU3_data['Group'].isnull())][['Title', 'Description', 'Duration']])
    print(IDU4_data[(IDU4_data['Type'] == 'TP') & (IDU4_data['Group'].isnull())][['Title', 'Description', 'Duration']])
    print(IDU5_data[(IDU5_data['Type'] == 'TP') & (IDU5_data['Group'].isnull())][['Title', 'Description', 'Duration']])

    save_data(IDU3_data, 'data/df/ADECal_IDU3_preprocessed.json')
    save_data(IDU4_data, 'data/df/ADECal_IDU4_preprocessed.json')
    save_data(IDU5_data, 'data/df/ADECal_IDU5_preprocessed.json')
