import pandas as pd
import re

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

    return df


if __name__ == "__main__":
    # Tests
    IDU3_data = load_data('data/json/ADECal_IDU3.json')
    preprocess_data(IDU3_data)
    print(IDU3_data.head(), IDU3_data.tail())

    IDU4_data = load_data('data/json/ADECal_IDU4.json')
    preprocess_data(IDU4_data)
    print(IDU4_data.head(), IDU4_data.tail())

    IDU5_data = load_data('data/json/ADECal_IDU5.json')
    preprocess_data(IDU5_data)
    print(IDU5_data.head(), IDU5_data.tail())

    print(IDU3_data[IDU3_data['Type'] == 'TP']['Group'].isnull().sum())
    print(IDU4_data[IDU4_data['Type'] == 'TP']['Group'].isnull().sum())
    print(IDU5_data[IDU5_data['Type'] == 'TP']['Group'].isnull().sum())

    print(IDU3_data[(IDU3_data['Type'] == 'TP') & (IDU3_data['Group'].isnull())][['Title', 'Description', 'Duration']])
    print(IDU4_data[(IDU4_data['Type'] == 'TP') & (IDU4_data['Group'].isnull())][['Title', 'Description', 'Duration']])
    print(IDU5_data[(IDU5_data['Type'] == 'TP') & (IDU5_data['Group'].isnull())][['Title', 'Description', 'Duration']])
