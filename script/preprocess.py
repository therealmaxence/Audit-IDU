import pandas as pd
import re
import os
from math import ceil

def load_data(file_path):
    return pd.read_json(file_path, orient='records')

def detect_type(row):
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

def detect_group(row):
    description = row.get('Description', '').upper()
    
    match = re.search(r'IDU-[345]-([A-Z]+\d?)', description)
    if match:
        return match.group(1)

    return None

def preprocess_data(df):
    # Calcul la durée
    df['Duration'] = pd.to_datetime(df['Ends']) - pd.to_datetime(df['Starts'])
    
    # Extrait le code du cours
    df['Code'] = df['Title'].str.extract(r'([A-Za-z]{4}\d{3})', expand=False)

    # Extrait le type de cours
    with_code_mask = df['Code'].notnull()
    df.loc[with_code_mask, 'Type'] = df[with_code_mask].apply(detect_type, axis=1)

    # Extrait le groupe de TP
    TP_mask = df['Type'] == 'TP'
    df.loc[TP_mask, 'Group'] = df[TP_mask].apply(detect_group, axis=1)

    df['Year'] = pd.Series(pd.NA, index=df.index, dtype='Int64')
    semester = df.loc[with_code_mask, 'Code'].str[4].astype(int)
    df.loc[with_code_mask, 'Year'] = semester.apply(lambda x: ceil(x / 2)).astype('Int64')

    df.sort_values(by=['Starts'], inplace=True)

    return df

def keep_important_only(df):
    df = df[df["Code"].notna()] # Garder que les lignes avec un code de cours

    idu3_mask = df['Year'] == 3
    groups = df[idu3_mask]["Group"].dropna().unique()
    # Si on a des groupes pour IDU3, ne garder que les TP qui ont le premier groupe (ou ceux sans groupe).
    if len(groups) > 0:
        # Conserver : toutes les lignes hors IDU3, ou les non-TP, ou les TP dont le groupe est null ou = first_group
        mask = (df['Year'] != 3) | (df['Type'] != 'TP') | ((df['Type'] == 'TP') & (df['Group'].isnull() | (df['Group'] == groups[0])))
        df = df[mask]

    return df

def load_and_preprocess(file_path):
    data = load_data(file_path)
    return preprocess_data(data)

def load_IDU_cals():
    IDU3_data = load_and_preprocess('data/json/ADECal_IDU3.json')
    IDU4_data = load_and_preprocess('data/json/ADECal_IDU4.json')
    IDU5_data = load_and_preprocess('data/json/ADECal_IDU5.json')
    return pd.concat([IDU3_data, IDU4_data, IDU5_data], ignore_index=True)

def save_data(df, file_path):
    os.makedirs('data/df', exist_ok=True)
    df.to_json(file_path, orient='records', indent=2, force_ascii=False)


if __name__ == "__main__":
    data = load_IDU_cals()

    print(data.head(), data.tail())
    print(data[data['Type'] == 'TP']['Group'].isnull().sum())
    print(data[(data['Type'] == 'TP') & (data['Group'].isnull())][['Title', 'Description', 'Duration']])
    
    save_data(data, 'data/df/ADECal_IDU_all_preprocessed.json')

    important_only = keep_important_only(data)
    save_data(important_only, 'data/df/ADECal_IDU_all_important.json')