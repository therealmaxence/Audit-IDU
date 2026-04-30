import pandas as pd
import re
from helpers import preprocess_data

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

    save_data(IDU3_data, 'data/df/ADECal_IDU3_preprocessed.json')
    save_data(IDU4_data, 'data/df/ADECal_IDU4_preprocessed.json')
    save_data(IDU5_data, 'data/df/ADECal_IDU5_preprocessed.json')
