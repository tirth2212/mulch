import json
import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_PARAMS = {
    'host': os.getenv("PG_HOST"),
    'port': os.getenv("PG_PORT"),
    'dbname': os.getenv("PG_DATABASE"),
    'user': os.getenv("PG_USER"),
    'password': os.getenv("PG_PASSWORD")
}

DATA_PATH = "json/api_out.json"
TRUCK_PATH = "json/truck.json"
TRUCK_LOC_PATH = "json/truck_location.json"

def get_or_create(cur, table, column, value):
    if not value:
        return None
    cur.execute(f"SELECT id FROM {table} WHERE {column} = %s", (value,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(f"INSERT INTO {table} ({column}) VALUES (%s) RETURNING id", (value,))
    return cur.fetchone()[0]

def extract_json_from_mixed_file(path):
    from collections import defaultdict

    with open(path, 'r') as file:
        lines = file.readlines()

    section = None
    data = defaultdict(list)
    current_headers = []
    capture = False

    for line in lines:
        line = line.strip()
        if line.endswith("Jobs:"):
            section = line.replace("Jobs:", "").strip()
            current_headers = []
            capture = False

        elif line.startswith("+--") and not current_headers:
            capture = True

        elif capture and line.startswith("|"):
            if not current_headers:
                current_headers = [col.strip() for col in line.strip('|').split('|')]
            else:
                values = [v.strip() for v in line.strip('|').split('|')]
                if len(values) == len(current_headers):
                    row = dict(zip(current_headers, values))
                    data[section].append(row)

        elif line.startswith("🚫") or line.startswith("📦") or line.startswith("+--"):
            continue

    return data

def sync_jobs():
    data = extract_json_from_mixed_file(DATA_PATH)

    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            for category, jobs in data.items():
                if not isinstance(jobs, list):
                    continue

                for job in jobs:
                    client_id = get_or_create(cur, 'clients', 'name', job.get("Client"))
                    material_id = get_or_create(cur, 'materials', 'name', job.get("Material"))
                    vendor_id = get_or_create(cur, 'material_vendors', 'name', job.get("Material Vendor"))
                    job_type_id = get_or_create(cur, 'job_types', 'name', job.get("Job Type"))
                    status_id = get_or_create(cur, 'job_statuses', 'name', job.get("Status"))

                    cur.execute("""
                        INSERT INTO jobs (
                            monday_id, name, client_id, status_id, material_id, vendor_id,
                            job_type_id, address, latitude, longitude, bid_qty, is_night_job
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (monday_id) DO UPDATE SET
                            name = EXCLUDED.name,
                            client_id = EXCLUDED.client_id,
                            status_id = EXCLUDED.status_id,
                            material_id = EXCLUDED.material_id,
                            vendor_id = EXCLUDED.vendor_id,
                            job_type_id = EXCLUDED.job_type_id,
                            address = EXCLUDED.address,
                            latitude = EXCLUDED.latitude,
                            longitude = EXCLUDED.longitude,
                            bid_qty = EXCLUDED.bid_qty,
                            is_night_job = EXCLUDED.is_night_job
                    """, (
                        job.get("Name"),
                        job.get("Name"),
                        client_id,
                        status_id,
                        material_id,
                        vendor_id,
                        job_type_id,
                        job.get("Address"),
                        float(job.get("Latitude") or 0),
                        float(job.get("Longitude") or 0),
                        float(job.get("Bid Qty") or 0),
                        job.get("Night?") == "✅ Yes"
                    ))
        conn.commit()
        print("✅ Jobs synced successfully.")

def sync_job_assignments():
    with open(TRUCK_PATH, 'r') as f:
        lines = f.readlines()

    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            vehicle_code = None
            for line in lines:
                line = line.strip()

                if line.startswith("==") and "(" in line and ")" in line:
                    parts = line.split("(")
                    vehicle_code = parts[0].strip("= 🛻").strip()
                    vehicle_id = get_or_create(cur, 'vehicles', 'code', vehicle_code)

                elif line.startswith("|") and vehicle_code:
                    parts = [p.strip() for p in line.strip('|').split('|')]
                    if len(parts) < 16:
                        continue

                    job_name = parts[8]
                    dispatch_status = parts[3]
                    load_status = parts[4]
                    date_str = parts[2]
                    qty_left = parts[5]
                    qty_installed = parts[6]

                    cur.execute("SELECT id FROM jobs WHERE name = %s", (job_name,))
                    job_row = cur.fetchone()
                    if not job_row:
                        continue

                    job_id = job_row[0]

                    try:
                        job_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    except:
                        continue

                    cur.execute("""
                        INSERT INTO job_assignments (
                            job_id, vehicle_id, date, dispatch_status, load_status, qty_left, qty_installed
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        job_id, vehicle_id, job_date, dispatch_status, load_status,
                        float(qty_left or 0), float(qty_installed or 0)
                    ))
        conn.commit()
        print("✅ Job assignments synced successfully.")


def sync_vehicle_status_history():
    if os.stat(TRUCK_LOC_PATH).st_size == 0:
        print("⚠️ truck_location.json is empty. Skipping vehicle status sync.")
        return

    try:
        with open(TRUCK_LOC_PATH, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("❌ truck_location.json is not valid JSON. Skipping vehicle status sync.")
        return

    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            for record in data:
                vehicle_code = record.get("VehicleNumber")
                vehicle_id = get_or_create(cur, 'vehicles', 'code', vehicle_code)

                content = record.get("ContentResource", {}).get("Value", {})
                timestamp = content.get("UpdateUTC")
                address = content.get("Address", {}).get("AddressLine1")
                latitude = content.get("Latitude")
                longitude = content.get("Longitude")
                speed = content.get("Speed")
                status = content.get("DisplayState")

                if not timestamp:
                    continue

                cur.execute("""
                    INSERT INTO vehicle_status_history (
                        vehicle_id, timestamp, status, address, latitude, longitude, speed
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    vehicle_id,
                    timestamp,
                    status,
                    address,
                    float(latitude or 0),
                    float(longitude or 0),
                    float(speed or 0)
                ))
        conn.commit()
        print("✅ Vehicle location history synced successfully.")



if __name__ == "__main__":
    sync_jobs()
    sync_job_assignments()
    sync_vehicle_status_history()
