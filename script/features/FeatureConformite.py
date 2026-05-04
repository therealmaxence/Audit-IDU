import os
import config
import pandas as pd
from .Feature import Feature

class FeatureConformite(Feature):
    def __init__(self):
        super().__init__({
            "ade" : os.path.join(config.PREPROCESSED_FOLDER, "ade_essential.json"),
            "maquette" : os.path.join(config.NORMALIZED_FOLDER, "learnagement_MAQUETTE_dependance_sequence.json")
        },
        {
            "conformite" : { "path": os.path.join(config.RESULT_FOLDER, "dependances_conformite.json"), "data": None },
            "sequences" : { "path": os.path.join(config.RESULT_FOLDER, "dependances_sequences.json"), "data": None },
            "restantes" : { "path": os.path.join(config.RESULT_FOLDER, "dependances_restantes.json"), "data": None },
        })

    def compute(self):
        sequences, restantes = self.build_sequences()
        non_conformites = self.check_conformity(sequences, self.df["ade"])
        self.outputs["sequences"]["data"] = pd.DataFrame(sequences)
        self.outputs["restantes"]["data"] = pd.DataFrame(restantes)
        self.outputs["conformite"]["data"] = pd.DataFrame([
            { "Code": code, "Issues": issues }
            for code, issues in non_conformites.items()
        ])
        self.save() 


    def build_sequences(self):
        dependencies_data = self.df["maquette"]
        dependencies_data['Seen'] = False

        sequences = [[]]

        row = dependencies_data.loc[dependencies_data["numero_precedent"].astype(int) == 1].iloc[0]

        # Parcours les dépendances pour construire les séquences
        while row is not None:
            dependencies_data.loc[row.name, 'Seen'] = True

            sequences[-1].append(row)

            next_mask = (dependencies_data["module_precedent"] == row["module_suivant"]) \
                                    & (dependencies_data["type_precedent"] == row["type_suivant"]) \
                                    & (dependencies_data["numero_precedent"] == row["numero_suivant"])
            next_rows = dependencies_data.loc[next_mask & (dependencies_data["Seen"] == False)]
            if not next_rows.empty:
                row = next_rows.iloc[0]
                continue
            else:
                start_rows = dependencies_data.loc[
                    (dependencies_data["numero_precedent"].astype(int) == 1)
                    & (dependencies_data["Seen"] == False)
                ]
                if not start_rows.empty:
                    row = start_rows.iloc[0]
                    sequences.append([])
                else:
                    row = None

        # Lignes restantes
        restantes = [dependencies_data.loc[dependencies_data["Seen"] == False].to_dict('records')]

        # Convertir au format (Code/Type/Numero)
        formatted_sequences = []
        for seq in sequences:
            seq_formatted = []
            for item in seq:
                seq_formatted.append({
                    'Code': item['module_precedent'][:7],
                    'Type': item['type_precedent'],
                    'Numero': item['numero_precedent'],
                })
            if seq:  # Ajouter le dernier suivant
                seq_formatted.append({
                    'Code': seq[-1]['module_suivant'][:7],
                    'Type': seq[-1]['type_suivant'],
                    'Numero': seq[-1]['numero_suivant'],
                })
            formatted_sequences.append(seq_formatted)
        
        # Récupérer les restantes (non visitées)
        restantes_raw = dependencies_data.loc[dependencies_data["Seen"] == False]
        restantes_formatted = []
        for item in restantes_raw.itertuples():
            restantes_formatted.append({
                'Code': item.module_precedent[:7],
                'Type': item.type_precedent,
                'Numero': item.numero_precedent,
            })
        
        return formatted_sequences, restantes_formatted


    def print_sequences(self, sequences):
        for i, seq in enumerate(sequences):
            seq_str = ' → '.join([f"{item['Code']} {item['Type']}{item['Numero']}" for item in seq])
            print(f"Sequence {i+1}: {seq_str}")


    def check_conformity(self, sequences, data):
        non_conformites = {}

        prev_date = None

        # Parcours les séquences pour vérifier la conformité
        for seq in sequences:
            for item in seq:
                code, type_, numero = item['Code'], item['Type'], int(item['Numero'])

                # Cherche la correspondance dans les données ADE
                match = data[
                    (data['Code'] == code) &
                    (data['Type'] == type_) &
                    (data['Numero'] == numero)
                ]

                # Si aucune correspondance n'est trouvée, c'est une non-conformité
                if match.empty:
                    non_conformites[code] = non_conformites.get(code, []) + [{
                        'Type': type_, 'Numero': numero, 'Reason': 'Introuvable dans ADE'
                    }]
                
                # Si une correspondance est trouvée, vérifier la temporalité
                else:
                    date = match.iloc[0]['Starts']

                    # Si date < prev_date: non-conformité temporelle
                    if prev_date and date < prev_date:
                        non_conformites[code] = non_conformites.get(code, []) + [{
                            'Type': type_, 'Numero': numero, 'Reason': f"Non-conformité temporelle ({prev_date} > {date})"
                        }]
                    
                    prev_date = date
            prev_date = None  # Réinitialiser la date pour la prochaine séquence

        return non_conformites

    def print_non_conformites(self, non_conformites):
        if non_conformites:
            print("\nNon-conformités détectées :")
            for code, issues in non_conformites.items():
                print(f"{code} :")
                for issue in issues:
                    print(f"  - {issue['Type']}{issue['Numero']} : {issue['Reason']}")
        else:
            print("\nToutes les séquences sont conformes aux données ADE.")