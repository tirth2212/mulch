import json
import os
from collections import defaultdict
from tabulate import tabulate

INPUT_FILES = {
    "Jobs": "json/api_out.json",
    "Truck Assignments": "json/truck.json",
    "Truck Locations": "json/truck_location.json"
}

OUTPUT_FILE = "json/visualization_summary.json"


def load_json(file_path):
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return None
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in {file_path}")
        return None


def visualize_jobs(data):
    summary = {}
    for category, rows in data.items():
        summary[category] = len(rows)
        print(f"\n📊 {category} Jobs ({len(rows)} entries):")
        print(tabulate(rows[:5], headers="keys", tablefmt="grid"))
    return summary


def visualize_truck_assignments(data):
    summary = defaultdict(lambda: defaultdict(int))
    for entry in data:
        vehicle = entry.get("vehicle")
        group = entry.get("group")
        rows = entry.get("data", [])
        summary[vehicle][group] = len(rows)
        print(f"\n🚚 {vehicle} - {group} ({len(rows)} entries):")
        if rows:
            print(tabulate(rows[:5], headers="keys", tablefmt="grid"))
    return summary


def visualize_truck_locations(data):
    print("\n📍 Truck Location Snapshots:")
    summary = {"Total Records": len(data)}
    for row in data[:5]:
        vehicle = row.get("VehicleNumber")
        timestamp = row.get("ContentResource", {}).get("Value", {}).get("UpdateUTC")
        status = row.get("ContentResource", {}).get("Value", {}).get("DisplayState")
        print(f"- {vehicle} @ {timestamp} — {status}")
    return summary


def main():
    all_summaries = {}

    jobs_data = load_json(INPUT_FILES["Jobs"])
    if jobs_data:
        all_summaries["Jobs"] = visualize_jobs(jobs_data)

    truck_data = load_json(INPUT_FILES["Truck Assignments"])
    if truck_data:
        all_summaries["Truck Assignments"] = visualize_truck_assignments(truck_data)

    loc_data = load_json(INPUT_FILES["Truck Locations"])
    if loc_data:
        all_summaries["Truck Locations"] = visualize_truck_locations(loc_data)

    # Save summary output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_summaries, f, indent=2)
    print(f"\n✅ Summary saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
