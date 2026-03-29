import csv
from typing import List, Dict

from dal.interfaces import IDataFileReader


class CsvFileReader(IDataFileReader):


    def read(self, file_path: str) -> List[Dict[str, str]]:
        rows = []
        with open(file_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if row.get("record_type", "").strip():
                    rows.append(dict(row))
        return rows
