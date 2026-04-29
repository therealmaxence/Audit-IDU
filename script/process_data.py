import re
from datetime import datetime
import json

def verif_seance_module(ade, nom_module):
    for seance in ade:
        match = re.match(r'^[^_\s]+', seance['Title'])
        if match and match.group(0) == nom_module:
            return True
    return False

def verif_seance_all_modules(ade, modules):
    res = []
    for module in modules:
        if not verif_seance_module(ade, module):
            res.append(module)
    return res

def get_type_cours(description):
    first_line = description.split('\n')[0]
    for type_str in ('CM', 'TD', 'TP'):
        if f'({type_str})' in first_line:
            return type_str
    return None

def get_duree_heures(starts, ends):
    t1 = datetime.fromisoformat(starts)
    t2 = datetime.fromisoformat(ends)
    return (t2 - t1).total_seconds() / 3600

def normaliser_titre(seance):

    if seance.get('code') is None:
        return None
    
    type_seance = seance.get('Type', seance.get('type')) 
    return f"{seance['code']}_{type_seance}"

def verif_volume_horaire(ade, nom_module, volume_CM, volume_TD, volume_TP):
    count = {'CM': 0.0, 'TD': 0.0, 'TP': 0.0}
    seen = set()

    for seance in ade:
        if seance['code'] != nom_module:
            continue

        if seance['type'] is None:
            continue

        date_jour = seance['Starts'][:10]  # "2025-11-24"
        titre_norm = normaliser_titre(seance)
        type_seance = seance['type']
        groupe = seance['groupe']

        if type_seance == 'TP' and re.match(r'^G[12]$', groupe):
            cle = titre_norm 
        else:
            # Comportement normal : on différencie par date
            cle = (titre_norm, date_jour)
        cle = (titre_norm, date_jour)

        if cle in seen:
            continue
        seen.add(cle)

        count[seance['type']] += get_duree_heures(seance['Starts'], seance['Ends'])

    if count['CM'] >= volume_CM and count['TD'] >= volume_TD and count['TP'] >= volume_TP:
        return "OK"
    else:
        return f"Volume horaire incorrect pour {nom_module} : CM={count['CM']}h (attendu {volume_CM}h), TD={count['TD']}h (attendu {volume_TD}h), TP={count['TP']}h (attendu {volume_TP}h)"

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

if __name__ == "__main__":
    
    with open('data/ADECal_IDU3.json', 'r') as f:
        ade3 = json.load(f)
    with open('data/ADECal_IDU4.json', 'r') as f:
        ade4 = json.load(f)
    with open('data/ADECal_IDU5.json', 'r') as f:
        ade5 = json.load(f)
    with open('data/MAQUETTE_IDU.json', 'r') as f:
        modules = json.load(f)


    print(proportion_module_present(ade3, modules))

    testNom = "INFO501"

    print(verif_volume_horaire(ade3, testNom, 12, 10.5, 16))