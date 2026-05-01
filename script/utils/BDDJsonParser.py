import json
import pandas as pd
from .Parser import Parser

class BDDJsonParser(Parser):
    def __init__(self):
        super().__init__(supported_extensions=[".json"])

    def __preprocess__(self, f):
        """Lit le contenu du fichier JSON et le convertit en une liste de dictionnaires."""
        try:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("Le fichier JSON doit contenir une liste d'objets.")
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Erreur de décodage JSON : {e}")
    
    def __parse__(self, raw):
        table = next(item for item in raw if item["type"] == "table")
        df = pd.DataFrame(table['data'])
        df.attrs["table"] = table.get("name", None)
        df.attrs["database"] = table.get("database", None)
        return df