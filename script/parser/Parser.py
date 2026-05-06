from abc import ABC, abstractmethod
import pandas as pd
import os
from pathlib import Path
 
class Parser(ABC):
    def __init__(self, supported_extensions: list[str] = []):
        self.supported_extensions = supported_extensions

    def __get_abspath__(self, path: str) -> str:
        """Valide et stocke le chemin local vers le fichier source.
        Retourne le chemin résolu."""
        resolved = os.path.abspath(path)

        if not os.path.isfile(resolved):
            raise FileNotFoundError(f"Le fichier '{resolved}' n'existe pas.")
        
        ext = os.path.splitext(resolved)[1].lower()
        if ext not in self.supported_extensions:
            raise ValueError(f"Extension de fichier '{ext}' non supportée. Extensions supportées : {self.supported_extensions}")

        return resolved

    @abstractmethod
    def __preprocess__(self, f):
        """Effectue les étapes de pré-traitement nécessaires avant le parsing."""
        pass

    def __load_file__(self, path: str):
        """Charge le fichier source et prépare les données pour le parsing."""
        abspath = self.__get_abspath__(path)
        with open(abspath, "r", encoding="utf-8") as f:
            raw = self.__preprocess__(f)
        return raw

    @abstractmethod
    def __parse__(self, raw) -> pd.DataFrame:
        """Parse le fichier chargé et retourne un DataFrame pandas."""
        pass

    def get_dataframe(self, path: str) -> pd.DataFrame:
        """Point d'entrée pour obtenir le DataFrame à partir du fichier source."""
        paths = []
        if Path(path).is_dir():
            for root, _, files in os.walk(path):
                for file in files:
                    paths.append(os.path.join(root, file))
        else:
            paths.append(path)
        
        dfs = []
        for _path in paths:
            raw = self.__load_file__(_path)
            dfs.append(self.__parse__(raw))
        return pd.concat(dfs, ignore_index=True)