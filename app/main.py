import subprocess
import datetime

def run_script(script_name, log_file):
    try:
        log_file.write(f"\n🚀 Running {script_name}...\n")
        result = subprocess.run(["python3", script_name], capture_output=True, text=True)
        log_file.write(result.stdout)
        log_file.write(result.stderr)

        if result.returncode == 0:
            log_file.write(f"✅ {script_name} completed successfully.\n")
            print(f"✅ {script_name} completed successfully.")
        else:
            log_file.write(f"⚠️ {script_name} finished with errors.\n")
            print(f"⚠️ {script_name} finished with errors.")

    except Exception as e:
        error_msg = f"❌ Failed to run {script_name}: {e}\n"
        log_file.write(error_msg)
        print(error_msg)

if __name__ == "__main__":
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("schedule_run.log", "a") as log_file:
        log_file.write(f"\n\n==== Schedule Run @ {timestamp} ====\n")
        
        run_script("loader.py", log_file)
        run_script("simulator.py", log_file)

        log_file.write("🎯 All steps finished. Check 'truck_schedule_output.txt' for the schedule.\n")

    print("\n🎯 All steps finished. Check 'truck_schedule_output.txt' and 'schedule_run.log'.")


