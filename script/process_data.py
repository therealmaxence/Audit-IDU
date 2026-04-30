import re
from datetime import datetime
import json


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


def proportion_module_present(ade, modules):

    modules_presents = []
    modules_absents = []
    modules_invalides = []
    
    for module in modules[2]['data']:
        code_brut = module['code_module']
        match = re.match(r'^[^_\s]+', code_brut)
        
        if match:
            nom_module = match.group(0)
            
            if verif_seance_module(ade, nom_module):
                modules_presents.append(nom_module)
            else:
                modules_absents.append(nom_module)
        else:
            modules_invalides.append(code_brut)
            
    total_valides = len(modules_presents) + len(modules_absents)
    
    if total_valides > 0:
        proportion = len(modules_presents) / total_valides 
    else:
        proportion = 0.0
        
    return {
        "proportion": proportion,
        "presents": modules_presents,
        "absents": modules_absents,
        "invalides": modules_invalides
    }

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

def proportion_volume_horaire_correct(ade, modules):
    total_modules = 0
    modules_corrects = 0

    for module in modules[2]['data']:
        code_brut = module['code_module']
        match = re.match(r'^[^_\s]+', code_brut)
        
        if match:
            nom_module = match.group(0)
            total_modules += 1
            if verif_volume_horaire(ade, nom_module, float(module['cm']), float(module['td']), float(module['tp'])) == "OK":
                modules_corrects += 1

    if total_modules > 0:
        proportion = modules_corrects / total_modules
    else:
        proportion = 0.0

    return {
        "proportion": proportion,
        "total_modules": total_modules,
        "modules_corrects": modules_corrects
    }


if __name__ == "__main__":
    
    with open('data/json/ADECal_IDU3.json', 'r') as f:
        ade3 = json.load(f)
    with open('data/json/ADECal_IDU4.json', 'r') as f:
        ade4 = json.load(f)
    with open('data/json/ADECal_IDU5.json', 'r') as f:
        ade5 = json.load(f)
    with open('data/json/MAQUETTE_IDU.json', 'r') as f:
        modules = json.load(f)


    print(proportion_module_present(ade3, modules))

    testNom = "INFO501"

    for ade in [ade3, ade4, ade5]:
        print(proportion_volume_horaire_correct(ade, modules))