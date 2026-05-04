import os
import re
import config
import pandas as pd
from .Preprocess import Preprocess
from .ADEPreprocess import PreprocessADE


class PreprocessModuleADE(Preprocess):
    def __init__(self):
        super().__init__(
            {
                "ade": os.path.join(config.PREPROCESSED_FOLDER, 'ade.json'),
                "modules": os.path.join(config.NORMALIZED_FOLDER, 'learnagement_MAQUETTE_module.json'),
            },
            {
                "module_ade": {"path": os.path.join(config.PREPROCESSED_FOLDER, 'module_ade.json'), "data": None},
            }
        )
        # helper to reuse ADEPreprocess methods
        self.ade_helper = PreprocessADE()

    def compute(self):
        self.outputs["module_ade"]["data"] = pd.DataFrame(self.compare_volume_horraire(self.df["ade"], self.df["modules"]))
        self.save()

    def verif_seance_module(self, ade, nom_module):
        if hasattr(ade, 'iterrows'):
            titles = ade['Title'].astype(str).str.extract(r'^([^_\s]+)')[0]
            return (titles == nom_module).any()

        # fallback original
        for seance in ade.itertuples(index=False):
            match = re.match(r'^[^_\s]+', seance.Title)
            if match and match.group(0) == nom_module:
                return True
        return False

    def verif_seance_all_modules(self, ade, modules):
        res = []
        for module in modules.itertuples(index=False):
            code_brut = module.code_module
            match = re.match(r'^[^_\s]+', code_brut)
            nom_module = match.group(0) if match else code_brut
            if not self.verif_seance_module(ade, nom_module):
                res.append(nom_module)
        return res

    def normaliser_titre(self, seance):
        code = seance['Code'] if isinstance(seance, pd.Series) else getattr(seance, 'Code', None)
        if pd.isna(code): return None

        Type_seance = seance['Type'] if isinstance(seance, pd.Series) else getattr(seance, 'Type', None)
        return f"{code}_{Type_seance}"

    def verif_volume_horaire(self, ade, nom_module, volume_CM, volume_TD, volume_TP):
        # ensure dataframe
        df = ade if hasattr(ade, 'iterrows') else pd.DataFrame(ade)
        df = df[df['Code'] == nom_module].dropna(subset=['Type']).copy()
        if df.empty:
            return (False, f"{nom_module} : CM=0.0h (attendu {volume_CM}h), TD=0.0h (attendu {volume_TD}h), TP=0.0h (attendu {volume_TP}h)")

        # compute normalized title and date
        df['date_jour'] = df['Starts'].astype(str).str[:10]
        df['titre_norm'] = df.apply(lambda r: self.normaliser_titre(r), axis=1)

        # compute duration using ADE helper
        df['duration_h'] = df.apply(lambda r: float(self.ade_helper.get_duration(r)), axis=1)

        # build deduplication key
        def make_key(r):
            return f"{r['titre_norm']}_{r['date_jour']}"

        df['key'] = df.apply(make_key, axis=1)
        df = df.drop_duplicates(subset=['key'])

        sums = df.groupby('Type')['duration_h'].sum().to_dict()
        cm = float(sums.get('CM', 0.0))
        td = float(sums.get('TD', 0.0))
        tp = float(sums.get('TP', 0.0))

        if cm >= float(volume_CM) and td >= float(volume_TD) and tp >= float(volume_TP):
            return (True, f"OK pour {nom_module} : CM={cm}h (attendu {volume_CM}h), TD={td}h (attendu {volume_TD}h), TP={tp}h (attendu {volume_TP}h)")
        else:
            return (False, f"{nom_module} : CM={cm}h (attendu {volume_CM}h), TD={td}h (attendu {volume_TD}h), TP={tp}h (attendu {volume_TP}h)")

    def count_volume_horaire_toJson(self, ade, nom_module, volume_CM=0.0, volume_TD=0.0, volume_TP=0.0):
        df = ade if hasattr(ade, 'iterrows') else pd.DataFrame(ade)
        df = df[df['Code'] == nom_module].dropna(subset=['Type']).copy()
        count = {'nom': nom_module, 'CM': {'attendu': float(volume_CM), 'reel': 0.0}, 'TD': {'attendu': float(volume_TD), 'reel': 0.0}, 'TP': {'attendu': float(volume_TP), 'reel': 0.0}}
        if df.empty:
            return count

        df['date_jour'] = df['Starts'].astype(str).str[:10]
        df['titre_norm'] = df.apply(lambda r: self.normaliser_titre(r), axis=1)
        df['duration_h'] = df.apply(lambda r: float(self.ade_helper.get_duration(r)), axis=1)

        def make_key(r):
            return f"{r['titre_norm']}_{r['date_jour']}"

        df['key'] = df.apply(make_key, axis=1)
        df = df.drop_duplicates(subset=['key'])

        sums = df.groupby('Type')['duration_h'].sum().to_dict()
        count['CM']['reel'] = float(sums.get('CM', 0.0))
        count['TD']['reel'] = float(sums.get('TD', 0.0))
        count['TP']['reel'] = float(sums.get('TP', 0.0))

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
                if self.ade_helper.get_year(nom_module) == annee:
                    total_modules += 1
                    ok, msg = self.verif_volume_horaire(ade, nom_module, float(module.cm), float(module.td), float(module.tp))
                    if ok:
                        modules_corrects += 1
                    else:
                        details_modules_incorrects.append(msg)

        proportion = (modules_corrects / total_modules) if total_modules > 0 else 0.0

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
                elif self.ade_helper.get_year(nom_module) == annee:
                    modules_absents.append(nom_module)
            else:
                modules_invalides.append(code_brut)

        total_valides = len(modules_presents) + len(modules_absents)
        proportion = (len(modules_presents) / total_valides) if total_valides > 0 else 0.0

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