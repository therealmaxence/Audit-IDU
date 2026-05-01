import os
import config
from utils import MoodleParser, ADEICSParser, BDDJsonParser

if __name__ == '__main__':
    # region: Normalize data files
    moodle_parser = MoodleParser()
    ade_parser = ADEICSParser()
    bdd_parser = BDDJsonParser()

    moodle = moodle_parser.get_dataframe(os.path.join(config.RAW_FOLDER, 'html'))
    ade = ade_parser.get_dataframe(os.path.join(config.RAW_FOLDER, 'ics'))
    bdds = []
    for root, _, files in os.walk(os.path.join(config.RAW_FOLDER, 'json')):
        for file in files:
            bdds.append(bdd_parser.get_dataframe(os.path.join(root, file)))
    
    moodle.to_json(os.path.join(config.NORMALIZED_FOLDER, 'moodle.json'), orient='records', force_ascii=False, indent=2)
    ade.to_json(os.path.join(config.NORMALIZED_FOLDER, 'ade.json'), orient='records', force_ascii=False, indent=2, date_format="iso")
    for bdd in bdds:
        table_name = bdd.attrs.get("table", "unknown_table")
        database_name = bdd.attrs.get("database", "unknown_database")
        filename = f"{database_name}_{table_name}.json"
        bdd.to_json(os.path.join(config.NORMALIZED_FOLDER, filename), orient='records', force_ascii=False, indent=2)
    # endregion
