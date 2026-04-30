import re
from datetime import datetime
import json

from helpers import (
    get_type_cours,
    get_duree_heures,
    normaliser_titre,
    verif_seance_module,
    verif_seance_all_modules,
    verif_volume_horaire,
    proportion_module_present,
)


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

    print(verif_volume_horaire(ade3, testNom, 12, 10.5, 16))