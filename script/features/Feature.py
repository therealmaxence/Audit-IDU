from abc import ABC, abstractmethod
from parser import JsonParser

class Feature(ABC):
    def __init__(self, files: dict[str, str] = {}):
        self.df = {}
        
        json_parser = JsonParser()
        for key, value in files.items():
            self.df[key] = json_parser.get_dataframe(value)
        

    @abstractmethod
    def compute(self):
        pass