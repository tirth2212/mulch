import requests
import json
from dotenv import load_dotenv
import os
import time
load_dotenv()

# Groq API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-8b-8192"
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

import re

def extract_json_block(text):
    """
    Extracts the first JSON object from a block of text.
    """
    match = re.search(r"{\s*\"truck\".*}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            print("❌ JSON structure found but could not be decoded.")
    return None

def call_groq_llm(prompt: str, truck_id: str):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    try:
        response = requests.post(GROQ_ENDPOINT, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"❌ Groq API error for {truck_id}: {response.status_code} - {response.text}")
            return {"truck": truck_id, "recommended_jobs": []}

        # Extract and clean JSON from text
        raw_text = response.json()["choices"][0]["message"]["content"]
        parsed = extract_json_block(raw_text)

        if parsed:
            return parsed
        else:
            print(f"❌ Could not parse JSON from Groq for truck {truck_id}")
            return {"truck": truck_id, "recommended_jobs": []}

    except Exception as e:
        print(f"❌ Exception for truck {truck_id}: {e}")
        return {"truck": truck_id, "recommended_jobs": []}



# Format and print schedule
def format_schedule(schedule_data):
    lines = []
    lines.append("=======================================")
    lines.append("Schedule:\n")

    for truck in schedule_data:
        lines.append(f"Truck: {truck['truck']}")
        lines.append("Jobs for Tomorrow:")
        lines.append("Job No. | Job’s Name                 | Material     | Address")
        for i, job in enumerate(truck["recommended_jobs"], start=1):
            lines.append(f"{i:<8} | {job['job_name']:<25} | {job['material']:<12} | {job['address']}")
        lines.append("")

    return "\n".join(lines)

# Load prompts
with open("../database/json/llm_prompts.json", "r") as f:
    llm_prompts = json.load(f)

# Schedule container
final_schedule = []

# Call Groq API for each truck
for entry in llm_prompts:
    truck_id = entry["truck_id"]
    prompt = entry["prompt"]

    print(f"📡 Sending prompt for Truck {truck_id}...")
    response = call_groq_llm(prompt, truck_id)
    print(response)
    if response and "recommended_jobs" in response:
        final_schedule.append(response)
    time.sleep(2)

# Format and save the output
schedule = format_schedule(final_schedule)

with open("truck_schedule_output.txt", "w") as f:
    f.write(schedule)

print("✅ Done. Schedule written to 'truck_schedule_output.txt'")
