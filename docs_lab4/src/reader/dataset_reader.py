
import csv
import json
import logging
import os
import urllib.request
import urllib.parse
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DatasetReader:

    SOCRATA_API_URL = "https://data.cityofnewyork.us/resource/dsyc-npkh.json"

    def __init__(self, local_path: str = "data/air_quality.csv",
                 api_url: str = None, limit: int = 500):
        self._local_path = local_path
        self._api_url = api_url or self.SOCRATA_API_URL
        self._limit = limit

    def fetch_and_save(self) -> str:

        os.makedirs(os.path.dirname(self._local_path) or ".", exist_ok=True)

        params = urllib.parse.urlencode({"$limit": self._limit, "$order": ":id"})
        url = f"{self._api_url}?{params}"

        logger.info(f"[DatasetReader] Завантаження {self._limit} записів з:\n  {url}")

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "AirQuality-Lab/1.0",
                }
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                raw_data = response.read().decode("utf-8")
                records: List[Dict[str, Any]] = json.loads(raw_data)

        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            logger.warning(
                f"[DatasetReader] API недоступний ({exc}). "
                "Генерація тестових даних (offline-режим)..."
            )
            records = self._generate_fallback_records()

        except Exception as exc:
            raise ConnectionError(
                f"Непередбачена помилка при завантаженні: {exc}"
            ) from exc

        if not records:
            raise ValueError("API повернув порожній результат.")

        logger.info(f"[DatasetReader] Отримано {len(records)} записів. Збереження у CSV...")

        fieldnames = list(records[0].keys())
        with open(self._local_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)

        logger.info(f"[DatasetReader] CSV збережено: {self._local_path}")
        return self._local_path

    def read(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self._local_path):
            logger.info(
                f"[DatasetReader] Файл '{self._local_path}' не знайдено. "
                "Запуск завантаження з API..."
            )
            self.fetch_and_save()

        records = []
        with open(self._local_path, "r", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:

                clean_row = {k: v for k, v in row.items() if v != ""}
                records.append(clean_row)

        logger.info(f"[DatasetReader] Зчитано {len(records)} записів з {self._local_path}")
        return records

    def _generate_fallback_records(self) -> List[Dict[str, Any]]:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from src.generate_sample_data import generate_records
        records = generate_records(self._limit)
        logger.info(f"[DatasetReader] Згенеровано {len(records)} тестових записів (offline-режим).")
        return records

    def get_summary(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not records:
            return {"total": 0}

        all_keys = set()
        for record in records:
            all_keys.update(record.keys())

        field_fill_rate = {}
        for key in sorted(all_keys):
            filled = sum(1 for r in records if key in r and r[key])
            field_fill_rate[key] = f"{filled}/{len(records)} ({filled/len(records)*100:.0f}%)"

        return {
            "total_records": len(records),
            "total_fields": len(all_keys),
            "fields": sorted(all_keys),
            "field_fill_rate": field_fill_rate,
            "sample_record": records[0] if records else None,
        }
