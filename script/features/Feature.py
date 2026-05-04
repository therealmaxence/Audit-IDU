from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from parser import JsonParser

import json
import pandas as pd

class Feature(ABC):
    def __init__(self, files: dict[str, str] | None = None, outputs: dict[str, dict[str, Any]] | None = None):
        self.df = {}
        self.outputs = outputs or {}

        json_parser = JsonParser()
        for key, value in (files or {}).items():
            self.df[key] = json_parser.get_dataframe(value)
        

    @abstractmethod
    def compute(self):
        pass

    def save(self):
        for key, value in self.outputs.items():
            data = value.get("data")
            if isinstance(data, pd.DataFrame):
                data.to_json(value["path"], orient='records', indent=2, force_ascii=False, date_format="iso")
            elif data is not None:
                with open(value["path"], 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)