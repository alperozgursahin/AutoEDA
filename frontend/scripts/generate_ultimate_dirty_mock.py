import csv
import random
from pathlib import Path


def build_rows():
    random.seed(7)
    cities = ["New York", "new york", " NY ", "Los Angeles", "los angeles", "LA", ""]
    departments = ["Finance", "finance", "FINANCE", "Sales", "sales", "HR", ""]
    rows = []
    for idx in range(1, 71):
        age = random.choice([25, 32, 41, 999, -5, "", 29, 36])
        salary = random.choice([42000, 55000, 73000, 9999999, -50000, "", 120000])
        score = random.choice([0.2, 0.5, 0.8, "Unknown", "", -2.5, 2.2])
        city = random.choice(cities)
        department = random.choice(departments)
        rows.append(
            [
                idx,
                random.choice(["Alice", "alice", "ALICE", "Bob", "BOB", "Carol"]),
                age,
                salary,
                score,
                city,
                department,
                random.choice(["yes", "Yes", "YES", "no", "No", ""]),
            ]
        )

    rows.extend([rows[5], rows[12], rows[20], rows[5], rows[30]])
    return rows


def main():
    output_path = Path(__file__).resolve().parents[2] / "ultimate_dirty_mock.csv"
    headers = ["ID", "Name", "Age", "Salary", "Score", "City", "Department", "ActiveFlag"]
    rows = build_rows()
    with output_path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.writer(file_obj)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()

