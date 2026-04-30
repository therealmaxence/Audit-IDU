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

def get_Type_cours(description):
    first_line = description.split('\n')[0]
    for Type_str in ('CM', 'TD', 'TP'):
        if f'({Type_str})' in first_line:
            return Type_str
    return None

def get_duree_heures(starts, ends):
    t1 = datetime.fromisoformat(starts)
    t2 = datetime.fromisoformat(ends)
    return (t2 - t1).total_seconds() / 3600

def normaliser_titre(seance):

    if seance['Code'] is None:
        return None
    
    Type_seance = seance['Type']
    return f"{seance['Code']}_{Type_seance}"

def verif_volume_horaire(ade, nom_module, volume_CM, volume_TD, volume_TP):
    count = {'CM': 0.0, 'TD': 0.0, 'TP': 0.0}
    seen = set()

    for seance in ade:
        if seance['Code'] != nom_module:
            continue

        if seance['Type'] is None:
            continue

        date_jour = seance['Starts'][:10]  # "2025-11-24"
        titre_norm = normaliser_titre(seance)
        Type_seance = seance['Type']
        groupe = seance['Group']

        if Type_seance == 'TP' and re.match(r'^G[12]$', groupe):
            cle = titre_norm 
        else:
            cle = (titre_norm, date_jour)
        cle = (titre_norm, date_jour)

        if cle in seen:
            continue
        seen.add(cle)

        count[seance['Type']] += get_duree_heures(seance['Starts'], seance['Ends'])

    if count['CM'] >= volume_CM and count['TD'] >= volume_TD and count['TP'] >= volume_TP:
        return "OK"
    else:
        return f"Volume horaire incorrect pour {nom_module} : CM={count['CM']}h (attendu {volume_CM}h), TD={count['TD']}h (attendu {volume_TD}h), TP={count['TP']}h (attendu {volume_TP}h)"
    
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
    
    with open('data\df\ADECal_IDU3_preprocessed.json', 'r') as f:
        ade3 = json.load(f)
    with open('data\df\ADECal_IDU4_preprocessed.json', 'r') as f:
        ade4 = json.load(f)
    with open('data\df\ADECal_IDU5_preprocessed.json', 'r') as f:
        ade5 = json.load(f)
    with open('data\json\MAQUETTE_IDU.json', 'r') as f:
        modules = json.load(f)


    print(proportion_module_present(ade3, modules))

    testNom = "INFO501"

    for ade in [ade3, ade4, ade5]:
        print(proportion_volume_horaire_correct(ade, modules))