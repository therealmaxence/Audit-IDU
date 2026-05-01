from bs4 import BeautifulSoup
import pandas as pd
import re
from .Parser import Parser

class MoodleParser(Parser):
    def __init__(self):
        super().__init__(supported_extensions=[".html"])

    def __preprocess__(self, f):
        """Lit le contenu du fichier HTML et le convertit en une liste de dictionnaires."""
        soup = BeautifulSoup(f, "html.parser")
        return soup.find_all("div", attrs={"data-courseid": True})
    
    def __parse__(self, raw):
        def match(sequence):
            a = sequence.select_one(".coursecat > a")
            if not a or not a.text:
                return False
            text = a.text
            idu = "Informatique, Données, Usages" in text # todo: Can be generalize on all sections
            promo = "Cours Transversaux" in text
            return idu or promo
        sequences = [seq for seq in raw if match(seq)]

        results = []
        for seq in sequences:
            a = seq.select_one(".coursename > a")
            if not a:
                continue
            
            title = a.get_text(strip=True)
            match = re.match(r"^([a-zA-Z0-9_]+)\s*-?\s*(.*)$", title)
            
            if not match:
                continue
            
            results.append({
                "code_module": match.group(1).split("_")[0],
                "nom": match.group(2),
                "teachers": [
                    {
                        "lastname": identity[0].strip() if len(identity) > 0 else "",
                        "firstname": identity[1].strip() if len(identity) > 1 else ""
                    }
                    for teacher in seq.select(".teachers > li")
                    if (a_t := teacher.select_one("a"))
                    and (identity := a_t.get_text(strip=True).split(","))
                ]
            })
        return pd.DataFrame(results)