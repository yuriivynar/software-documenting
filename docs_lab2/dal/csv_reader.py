import csv
from typing import List, Dict
from dal.interfaces import IDataFileReader

SUPPORTED_DELIMITERS = {",": "comma (,)", ";": "semicolon (;)"}


def detect_delimiter(file_path: str) -> str:
    with open(file_path, newline="", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            return ";" if line.count(";") > line.count(",") else ","
    return ","


class CsvFileReader(IDataFileReader):
    def read(self, file_path: str, delimiter: str = "auto") -> List[Dict[str, str]]:
        if delimiter == "auto":
            resolved = detect_delimiter(file_path)
        elif delimiter in SUPPORTED_DELIMITERS:
            resolved = delimiter
        else:
            raise ValueError(f"Unsupported delimiter: {delimiter!r}. Use 'auto', ',' or ';'.")

        rows: List[Dict[str, str]] = []
        with open(file_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh, delimiter=resolved)
            for row in reader:
                if row.get("record_type", "").strip():
                    rows.append(dict(row))
        return rows