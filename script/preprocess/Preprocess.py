from abc import ABC, abstractmethod
from parser import JsonParser
import os

class Preprocess(ABC):
    def __init__(self, files: dict[str, str] = {}, outputs: dict[str, str] = {}):
        self.df = {}
        self.outputs = outputs
        
        json_parser = JsonParser()
        for key, value in files.items():
            self.df[key] = json_parser.get_dataframe(value)
        
    @abstractmethod
    def compute(self):
        pass

    def save(self):
        for key, value in self.outputs.items():
            value["data"].to_json(value["path"], orient='records', indent=2, force_ascii=False, date_format="iso")