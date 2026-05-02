import os
import re
from datetime import datetime
import config
import pandas as pd
from .Preprocess import Preprocess

class PreprocessModuleADE(Preprocess):
    def __init__(self):
        super().__init__(
            {
                "ade" : os.path.join(config.PREPROCESSED_FOLDER, 'ade.json'),
                "modules" : os.path.join(config.NORMALIZED_FOLDER, 'learnagement_MAQUETTE_module.json'),
            },
            {
                "module_ade" : { "path": os.path.join(config.PREPROCESSED_FOLDER, 'module_ade.json'), "data": None },
            }
        )
    
    def compute(self):
        self.outputs["module_ade"]["data"] = pd.DataFrame(self.compare_volume_horraire(self.df["ade"], self.df["modules"]))
        self.save()

    def get_annee_from_code(self, code):
        match = re.match(r'^[A-Za-z]{4}(\d{3})', code)
        
        if match:
            premier_chiffre = int(match.group(1)[0])
            
            if premier_chiffre in [5, 6]:
                return 3
            elif premier_chiffre in [7, 8]:
                return 4
            elif premier_chiffre == 9:
                return 5
                
        return None

    def verif_seance_module(self, ade, nom_module):
        for seance in ade.itertuples(index=False):
            match = re.match(r'^[^_\s]+', seance.Title)
            if match and match.group(0) == nom_module:
                return True
        return False

    def verif_seance_all_modules(self, ade, modules):
        res = []
        for module in modules.itertuples(index=False):
            if not self.verif_seance_module(ade, module):
                res.append(module)
        return res

    def get_Type_cours(self, description):
        first_line = description.split('\n')[0]
        for Type_str in ('CM', 'TD', 'TP'):
            if f'({Type_str})' in first_line:
                return Type_str
        return None

    def get_duree_heures(self, starts, ends):
        t1 = datetime.fromisoformat(starts)
        t2 = datetime.fromisoformat(ends)
        return (t2 - t1).total_seconds() / 3600

    def normaliser_titre(self, seance):

        if pd.isna(seance.Code):
            return None
        
        Type_seance = seance.Type
        return f"{seance.Code}_{Type_seance}"

    def verif_volume_horaire(self, ade, nom_module, volume_CM, volume_TD, volume_TP):
        count = {'CM': 0.0, 'TD': 0.0, 'TP': 0.0}
        seen = set()

        for seance in ade:
            if seance.Code != nom_module:
                continue

            if pd.isna(seance.Type):
                continue

            date_jour = seance.Starts[:10]  # "2025-11-24"
            titre_norm = self.normaliser_titre(seance)
            Type_seance = seance.Type
            groupe = seance.Group

            if Type_seance == 'TP' and re.match(r'^G[12]$', groupe):
                cle = titre_norm 
            else:
                cle = (titre_norm, date_jour)
            cle = (titre_norm, date_jour)

            if cle in seen:
                continue
            seen.add(cle)

            count[seance.Type] += self.get_duree_heures(seance.Starts, seance.Ends)

        if count['CM'] >= volume_CM and count['TD'] >= volume_TD and count['TP'] >= volume_TP:
            return (True, f"OK pour {nom_module} : CM={count['CM']}h (attendu {volume_CM}h), TD={count['TD']}h (attendu {volume_TD}h), TP={count['TP']}h (attendu {volume_TP}h)")
        else:
            return (False, f"{nom_module} : CM={count['CM']}h (attendu {volume_CM}h), TD={count['TD']}h (attendu {volume_TD}h), TP={count['TP']}h (attendu {volume_TP}h)")

    def count_volume_horaire_toJson(self, ade, nom_module, volume_CM=0.0, volume_TD=0.0, volume_TP=0.0):
        count = {'nom': nom_module, 'CM': {'attendu': float(volume_CM), 'reel': 0.0}, 'TD': {'attendu': float(volume_TD), 'reel': 0.0}, 'TP': {'attendu': float(volume_TP), 'reel': 0.0}}
        seen = set()

        for seance in ade.itertuples(index=False):
            if seance.Code != nom_module:
                continue

            if pd.isna(seance.Type):
                continue

            date_jour = seance.Starts[:10]  # "2025-11-24"
            titre_norm = self.normaliser_titre(seance)
            Type_seance = seance.Type
            groupe = seance.Group

            if Type_seance == 'TP' and re.match(r'^G[12]$', groupe):
                cle = titre_norm 
            else:
                cle = (titre_norm, date_jour)
            cle = (titre_norm, date_jour)

            if cle in seen:
                continue
            seen.add(cle)

            count[seance.Type]['reel'] += self.get_duree_heures(seance.Starts, seance.Ends)

        return count
        
    def proportion_volume_horaire_correct(self, ade, modules, annee):
        total_modules = 0
        modules_corrects = 0
        details_modules_incorrects = []

        for module in modules.itertuples(index=False):
            code_brut = module.code_module
            match = re.match(r'^[^_\s]+', code_brut)
            
            if match:
                nom_module = match.group(0)
                if self.get_annee_from_code(nom_module) == annee:
                    total_modules += 1
                    if self.verif_volume_horaire(ade, nom_module, float(module.cm), float(module.td), float(module.tp))[0]:
                        modules_corrects += 1
                    else:
                        details_modules_incorrects.append(self.verif_volume_horaire(ade, nom_module, float(module.cm), float(module.td), float(module.tp))[1])
        if total_modules > 0:
            proportion = modules_corrects / total_modules
        else:
            proportion = 0.0

        return {
            "proportion": proportion,
            "total_modules": total_modules,
            "modules_corrects": modules_corrects,
            "détails_modules_incorrects": details_modules_incorrects
        }

    def proportion_module_present(self, ade, modules, annee):

        modules_presents = []
        modules_absents = []
        modules_invalides = []
        
        for module in modules.itertuples(index=False):
            code_brut = module.code_module
            match = re.match(r'^[^_\s]+', code_brut)
            
            if match:
                nom_module = match.group(0)
                
                if self.verif_seance_module(ade, nom_module):
                    modules_presents.append(nom_module)
                elif self.get_annee_from_code(nom_module) == annee:
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
    def compare_volume_horraire(self, ade, modules):
        resultats = []

        for module in modules.itertuples(index=False):
            code_brut = module.code_module
            match = re.match(r'^[^_\s]+', code_brut)
            
            if match:
                nom_module = match.group(0)
                resultats.append(self.count_volume_horaire_toJson(ade, nom_module, module.cm, module.td, module.tp))

        return resultats