import os
import config
import pandas as pd
from .Feature import Feature

class FeatureTracability(Feature):
    def __init__(self):
        super().__init__({
            "moodle" : os.path.join(config.NORMALIZED_FOLDER, "moodle.json"),
            "maquette" : os.path.join(config.NORMALIZED_FOLDER, "learnagement_MAQUETTE_module.json"),
            "responsables" : os.path.join(config.NORMALIZED_FOLDER, "learnagement_LNM_enseignant.json"),
            "ade" : os.path.join(config.PREPROCESSED_FOLDER, "module_ade.json")
        })

    def compute(self):
        results = []
        for module in self.df["maquette"].itertuples(index=False):
            code = module.code_module.split("_")[0]
            responsable = next(
                (r for r in self.df["responsables"].itertuples(index=False)
                    if r.code_module.split("_")[0] == code)
                ,None
            )
            moodle_module = next(
                (m for m in self.df["moodle"].itertuples(index=False)
                    if m.code_module == code)
                ,None
            )

            has_responsable = False
            if responsable and moodle_module:
                teachers = getattr(moodle_module, "teachers", [])
                has_responsable = any(
                    t.get("lastname", "").lower() == responsable.nom.lower()
                    for t in teachers
                )

            ade_module = next(
                (m for m in self.df["ade"].itertuples(index=False)
                    if m.nom == code),
                None
            )

            # Moodle section
            result = module._asdict()
            result["moodle"] = {
                "nom": getattr(moodle_module, "nom", None) if moodle_module else None,
                "responsable": (
                    {
                        "nom": responsable.nom,
                        "prenom": responsable.prenom
                    } if has_responsable else None
                )
            }
            result['ade'] = {
                "cm": ade_module.CM['reel'] if ade_module else None,
                "td": ade_module.TD['reel'] if ade_module else None,
                "tp": ade_module.TP['reel'] if ade_module else None
            }
            # ADE section
            results.append(result)

        results = pd.DataFrame(results)
        results.to_json(os.path.join(config.RESULT_FOLDER, "tracability.json"), orient='records', force_ascii=False, indent=2)
        return results