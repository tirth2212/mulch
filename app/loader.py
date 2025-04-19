# Assemble a full script piece-by-piece, starting with loading and parsing all 3 files
import json
import pandas as pd
from geopy.distance import distance
from datetime import datetime

# === Load data files ===
with open("../database/json/truck_location.json", "r") as f:
    truck_location_data = json.load(f)

with open("../database/json/truck.json", "r") as f:
    truck_schedule_data = json.load(f)

with open("../database/json/api_out.json", "r") as f:
    jobs_data_raw = json.load(f)

# === STEP 1: Parse truck location info ===
truck_locations = []
for entry in truck_location_data:
    if entry["StatusCode"] == 200:
        vnum = entry["VehicleNumber"]
        val = entry["ContentResource"]["Value"]
        truck_locations.append({
            "vehicle_number": vnum,
            "latitude": val["Latitude"],
            "longitude": val["Longitude"],
            "address": val["Address"]["AddressLine1"],
            "city": val["Address"]["Locality"],
            "status": val["DisplayState"]
        })

df_truck_locations = pd.DataFrame(truck_locations)

# === STEP 2: Parse truck materials from truck.json Production Review ===
truck_materials = {}
for entry in truck_schedule_data:
    if entry["group"] == "Production Review":
        vehicle = entry["vehicle"]
        jobs = entry["data"]
        for job in reversed(jobs):  # use reversed to get the latest entry
            qty_left = job.get("Quantity Left on Truck", "")
            material = job.get("Material", "").strip()
            if qty_left and qty_left not in ["0", "0.0", ""]:
                truck_materials[vehicle] = {
                    "material": material,
                    "quantity_left": float(qty_left)
                }
                break

# Merge truck material info
df_truck_locations["material"] = df_truck_locations["vehicle_number"].map(
    lambda v: truck_materials.get(v, {}).get("material", ""))
df_truck_locations["quantity_left"] = df_truck_locations["vehicle_number"].map(
    lambda v: truck_materials.get(v, {}).get("quantity_left", 0.0))

# === STEP 3: Parse "Jobs to be Scheduled" from api_out.json ===
jobs_to_be_scheduled = jobs_data_raw.get("Jobs to be Scheduled", [])
parsed_jobs = []
for job in jobs_to_be_scheduled:
    parsed_jobs.append({
        "name": job.get("Name", "").strip(),
        "client": job.get("Client", "").strip(),
        "status": job.get("Status", "").strip(),
        "material": job.get("Material", "").strip(),
        "bid_qty": float(job.get("Bid Qty", 0) or 0),
        "address": job.get("Job Address", "").strip(),
        "job_type": (job.get("Job Type") or "").strip(),
        "latitude": job.get("Latitude", None),
        "longitude": job.get("Longitude", None),
        "night_access": str(job.get("Night?", "")).lower() == "yes"
    })

df_jobs_to_schedule = pd.DataFrame(parsed_jobs)
df_jobs_to_schedule = df_jobs_to_schedule.dropna(subset=["latitude", "longitude"])

# === STEP 4: Match jobs for each truck based on material and 40-mile radius ===
def find_jobs_for_truck(truck_row):
    truck_coords = (truck_row["latitude"], truck_row["longitude"])
    material = truck_row["material"]
    is_empty = not material
    nearby = []

    for _, job in df_jobs_to_schedule.iterrows():
        job_coords = (job["latitude"], job["longitude"])
        job_distance = distance(truck_coords, job_coords).miles

        if job_distance <= 40:
            if is_empty or job["material"] == material:
                job_entry = job.to_dict()
                job_entry["distance_miles"] = round(job_distance, 2)
                nearby.append(job_entry)

    return nearby

# === STEP 5: Generate LLM prompts ===
llm_prompts = []
llm_input_data = []

for _, truck_row in df_truck_locations.iterrows():
    truck_id = truck_row["vehicle_number"]
    nearby_jobs = find_jobs_for_truck(truck_row)
    
    if not nearby_jobs:
        continue

    truck_data = {
        "truck_id": truck_id,
        "location": {
            "latitude": truck_row["latitude"],
            "longitude": truck_row["longitude"],
            "city": truck_row["city"],
            "address": truck_row["address"]
        },
        "material": truck_row["material"],
        "quantity_left": truck_row["quantity_left"],
        "jobs": sorted(nearby_jobs, key=lambda j: j["distance_miles"])[:10]
    }
    llm_input_data.append(truck_data)

    job_descriptions = []
    for idx, job in enumerate(truck_data["jobs"], start=1):
        job_descriptions.append(
            f"{idx}. {job['name']} — Material: {job['material']}, "
            f"Bid Qty: {job['bid_qty']} yards, Distance: {job['distance_miles']} miles, "
            f"Night Access: {'Yes' if job['night_access'] else 'No'}"
        )

    prompt = f"""
You are a scheduling assistant for mulch delivery trucks.

Truck ID: {truck_id}
Location: {truck_row['address']} ({truck_row['latitude']}, {truck_row['longitude']})
Material on board: {truck_row['material'] or 'None (empty)'}
Quantity left on truck: {truck_row['quantity_left']} yards
Truck max capacity: 40 yards

Here are 10 nearby jobs to choose from:
{chr(10).join(job_descriptions)}

Instructions:
1. Select 2–3 jobs from the list for this truck to perform tomorrow.
2. If truck is empty or has less than 10 yards left, ask to fill up with 40 yards of mulch.
3. Prefer jobs with night access first (can start at 5 AM), otherwise default start is 7 AM.
4. Only pick jobs within 40 miles.
5. Return your recommendation in JSON format like this:

{{
  "truck": "{truck_id}",
  "recommended_jobs": [
    {{
      "job_name": "Job Name",
      "material": "Material",
      "bid_qty": 20,
      "start_time": "5:00 AM",
      "address": "Full address"
    }}
  ]
}}
""".strip()

    llm_prompts.append({
        "truck_id": truck_id,
        "prompt": prompt
    })

# Display one sample prompt (you'll wire this into Groq next)
llm_prompts[0]

with open("../database/json/llm_prompts.json", "w") as f:
    json.dump(llm_prompts, f)