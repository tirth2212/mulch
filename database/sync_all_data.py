import subprocess
import os
from datetime import datetime
import time
# List of data extraction scripts
DATA_SCRIPTS = [
    "Main_Data.py",
    "Team_Data.py",
    "truck_location.py"
]

# Path to the sync script
SYNC_SCRIPT = "sync_jobs_data.py"

MAX_RETRIES = 3
WAIT_SECONDS = 20

def run_script(script):
    print(f"\n▶️ Running {script}...")
    for attempt in range(MAX_RETRIES):
        print("Running script: ", script)
        #print current directory
        print("Current directory: ", os.getcwd())
        result = subprocess.run(["python", script], capture_output=True, text=True)
        print("Result: ", result)
        if result.returncode == 0:
            print(f"✅ {script} completed successfully.")
            print(result.stdout)
            return
        else:
            print(f"❌ Attempt {attempt + 1} failed running {script}:")
            print(result.stderr)
            if attempt < MAX_RETRIES - 1:
                print(f"⏳ Retrying {script} in {WAIT_SECONDS} seconds...")
                time.sleep(WAIT_SECONDS)
            else:
                print(f"🚫 Giving up on {script} after {MAX_RETRIES} attempts.")


def main():
    print("\n🚀 Starting full data refresh process...")

    for script in DATA_SCRIPTS:
        if os.path.exists(script):
            run_script(script)
        else:
            print(f"⚠️ Script not found: {script}")

    if os.path.exists(SYNC_SCRIPT):
        run_script(SYNC_SCRIPT)
    else:
        print(f"⚠️ Sync script not found: {SYNC_SCRIPT}")

    print("\n✅ All data updated and synced to the database.")
    print(f"✅ Webhook received at {datetime.now()}")


if __name__ == "__main__":
    main()