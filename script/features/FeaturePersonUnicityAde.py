import os
import config
import pandas as pd
from .Feature import Feature

class FeaturePersonUnicityADE(Feature):
    pass
    def __init__(self):
        pass
    #     super().__init__({
    #         "ade" : os.path.join(config.PREPROCESSED_FOLDER, "ade_essential.json"),
    #     },
    #     {
    #         "person_unicity" : { "path": os.path.join(config.RESULT_FOLDER, "person_unicity_ade.json"), "data": None },
    #     })
    
    def compute(self):
        pass
    #     person_unicity_data = self.df["ade"].groupby("Person").size().reset_index(name='Count')
    #     self.outputs["person_unicity"]["data"] = person_unicity_data
    #     self.save() 
    #     return self.outputs["person_unicity"]["data"]