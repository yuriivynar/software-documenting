
import csv
import os
import random
from datetime import datetime, timedelta

LOCATIONS = [
    "Building 1, Floor 1", "Building 1, Floor 2", "Building 1, Floor 3",
    "Building 2, Floor 1", "Building 2, Floor 2",
    "Building 3, Lobby", "Building 4, Hallway A", "Building 4, Hallway B",
    "Community Center", "Recreation Room", "Laundry Room",
    "Storage Room A", "Storage Room B", "Basement Level 1",
]

POLLUTANTS = [
    ("Carbon Monoxide", "CO", "ppm", (0.1, 2.5)),
    ("Nitrogen Dioxide", "NO2", "ppb", (5, 45)),
    ("Particulate Matter 2.5", "PM2.5", "µg/m³", (4, 25)),
    ("Particulate Matter 10", "PM10", "µg/m³", (10, 50)),
    ("Volatile Organic Compounds", "VOC", "ppb", (20, 200)),
    ("Carbon Dioxide", "CO2", "ppm", (400, 1200)),
    ("Formaldehyde", "HCHO", "ppb", (2, 25)),
    ("Ozone", "O3", "ppb", (15, 70)),
    ("Radon", "Rn", "pCi/L", (0.4, 4.0)),
    ("Relative Humidity", "RH", "%", (35, 65)),
]

STATUSES = ["Pass", "Pass", "Pass", "Pass", "Fail", "Borderline"]

INSPECTORS = [
    "J. Williams", "M. Rodriguez", "A. Chen", "D. Thompson",
    "S. Patel", "L. Johnson", "K. Martinez",
]

BASE_DATE = datetime(2017, 3, 1)

def generate_records(n: int = 500) -> list:
    records = []
    for i in range(1, n + 1):
        pollutant_name, symbol, unit, (lo, hi) = random.choice(POLLUTANTS)
        value = round(random.uniform(lo, hi), 2)
        date = BASE_DATE + timedelta(days=random.randint(0, 560))
        location = random.choice(LOCATIONS)
        status = "Fail" if value > hi * 0.9 else ("Borderline" if value > hi * 0.75 else "Pass")

        records.append({
            "unique_key": str(100000 + i),
            "test_date": date.strftime("%Y-%m-%dT%H:%M:%S"),
            "location": location,
            "building_address": "310 Rockaway Ave, Brooklyn, NY 11212",
            "borough": "Brooklyn",
            "community_board": "5",
            "pollutant_name": pollutant_name,
            "pollutant_symbol": symbol,
            "result_value": str(value),
            "unit_of_measurement": unit,
            "status": status,
            "action_required": "Yes" if status == "Fail" else "No",
            "inspector": random.choice(INSPECTORS),
            "latitude": str(round(40.6635 + random.uniform(-0.002, 0.002), 6)),
            "longitude": str(round(-73.9175 + random.uniform(-0.002, 0.002), 6)),
        })

    return records

def save_to_csv(records: list, path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fieldnames = list(records[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"[SampleData] Створено {len(records)} записів → {path}")

if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    path = sys.argv[2] if len(sys.argv) > 2 else "data/air_quality.csv"
    records = generate_records(n)
    save_to_csv(records, path)
