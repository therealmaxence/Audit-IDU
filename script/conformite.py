import json
import os
import pandas as pd

def build_sequences():
    with open('data/json/dependance_sequence_IDU.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Récupérer que la partie 'data' du fichier
    dependencies_data = [item['data'] for item in data if item.get('type') == 'table' and 'data' in item][0]
    dependencies_data = pd.DataFrame(dependencies_data)
    dependencies_data['Seen'] = False

    sequences = [[]]

    row = dependencies_data.loc[dependencies_data["numero_precedent"].astype(int) == 1].iloc[0]
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

    return sequences, restantes


def save_sequences(sequences, file_path):
    out = []
    for seq in sequences:
        seq_out = []
        for item in seq:
            seq_out.append({
                'Code': item['module_precedent'],
                'Type': item['type_precedent'],
                'Numero': item['numero_precedent'],
            })
        seq_out.append({
            'Code': seq[-1]['module_suivant'],
            'Type': seq[-1]['type_suivant'],
            'Numero': seq[-1]['numero_suivant'],
        })
        out.append(seq_out)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=4)


def print_sequences(sequences):
    for i, seq in enumerate(sequences):
        print(f"Sequence {i+1}:")
        for item in seq:
            print(f"  {item['module_precedent']} {item['type_precedent']} {item['numero_precedent']} -> "
                  f"{item['module_suivant']} {item['type_suivant']} {item['numero_suivant']}")
        print()


if __name__ == "__main__":
    sequences, restantes = build_sequences()
    print_sequences(sequences)

    os.makedirs('data/processed', exist_ok=True)
    save_sequences(sequences, 'data/processed/dependances_sequences_IDU.json')
    save_sequences(restantes, 'data/processed/dependances_restantes_IDU.json')