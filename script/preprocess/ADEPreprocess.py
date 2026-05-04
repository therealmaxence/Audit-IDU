import os
import re
from math import ceil
import config
import pandas as pd
from .Preprocess import Preprocess

class PreprocessADE(Preprocess):
    def __init__(self):
        super().__init__(
            { "ade" : os.path.join(config.NORMALIZED_FOLDER, 'ade.json')},
            {
                "ade" : { "path": os.path.join(config.PREPROCESSED_FOLDER, 'ade.json'), "data": None },
                "essential" : { "path": os.path.join(config.PREPROCESSED_FOLDER, 'ade_essential.json'), "data": None },
            }
        )

    def compute(self):
        self.outputs["ade"]["data"] = self.preprocess_data(self.df["ade"])
        self.outputs["essential"]["data"] = self.keep_important_only(self.outputs["ade"]["data"])
        self.save()

    def get_duration(self, row):
        start = pd.to_datetime(row['Starts'])
        end = pd.to_datetime(row['Ends'])
        return (end - start).total_seconds() / 3600.0

    def get_code(self, title):
        match = re.search(r'([A-Za-z]{4}\d{3})', title)
        return match.group(0) if match else None

    def get_type(self, row):
        text = row.get('Title', '') + ' ' + row.get('Description', '')
        text = text.upper()

        def base_regex(pattern):
            return r'(\b|_)' + pattern + r'(\b|_)'

        if re.search(base_regex(r'EXAMEN'), text):
            return 'CM'
        elif re.search(base_regex(r'CM'), text):
            return 'CM'
        elif re.search(base_regex(r'TD'), text):
            return 'TD'
        elif re.search(base_regex(r'TP'), text):
            return 'TP'
        else:
            return None

    def get_group(self, row):
        description = row.get('Description', '').upper()
        
        match = re.search(r'IDU-[345]-([A-Z]+\d?)', description)
        if match:
            return match.group(1)

        return None

    def get_year(self, code):
        if pd.isna(code) or len(code) < 5: return None
        return int(ceil(int(code[4]) / 2))

    def preprocess_data(self, df):
        # Calcul la durée
        df['Duration'] = df.apply(self.get_duration, axis=1)
        
        # Extrait le code du cours
        df['Code'] = df['Title'].apply(self.get_code)
        
        # Extrait le type de cours
        with_code_mask = df['Code'].notnull()
        df.loc[with_code_mask, 'Type'] = df[with_code_mask].apply(self.get_type, axis=1)

        # Extrait le groupe de TP
        TP_mask = df['Type'] == 'TP'
        df.loc[TP_mask, 'Group'] = df[TP_mask].apply(self.get_group, axis=1)

        # Extrait l'année (3, 4 ou 5)
        df['Year'] = df['Code'].apply(self.get_year).astype('Int64')

        df.sort_values(by=['Starts'], inplace=True)

        return df

    def keep_important_only(self, df):
        df = df[df["Code"].notna()] # Garder que les lignes avec un code de cours

        idu3_mask = df['Year'] == 3
        groups = df[idu3_mask]["Group"].dropna().unique()
        # Si on a des groupes pour IDU3, ne garder que les TP qui ont le premier groupe (ou ceux sans groupe).
        if len(groups) > 0:
            # Conserver : toutes les lignes hors IDU3, ou les non-TP, ou les TP dont le groupe est null ou = first_group
            mask = (df['Year'] != 3) | (df['Type'] != 'TP') | ((df['Type'] == 'TP') & (df['Group'].isnull() | (df['Group'] == groups[0])))
            df = df[mask]

        # Ajoute les numéros
        df['Numero'] = (df.groupby(['Code', 'Type']).cumcount() + 1).astype('Int64')

        return df