import os
import config
from .Feature import Feature

class FeatureCountModuleOccurence(Feature):
    def __init__(self):
        super().__init__({
            "ade" : os.path.join(config.PREPROCESSED_FOLDER, "ade_essential.json"),
        },
        {
            "count_module_occurence" : { "path": os.path.join(config.RESULT_FOLDER, "count_module_occurence.json"), "data": None },
        })

    def count_global(self):
        counts = self.df["ade"].groupby(['Code', 'Title']).size().reset_index(name='occurences')
        
        return [
            {
                "racine": code,
                "total_occurences": int(group['occurences'].sum()),
                "variantes": sorted([
                    {
                        "code": title,
                        "suffixe": "" if title == code else title[len(code):],
                        "occurences": int(occ)
                    }
                    for _, (_, title, occ) in group[['Code', 'Title', 'occurences']].iterrows()
                ], key=lambda x: x['occurences'], reverse=True)
            }
            for code, group in counts.groupby('Code')
        ]

    def compute(self):
        count_data = self.count_global()
        self.outputs["count_module_occurence"]["data"] = count_data
        self.save()