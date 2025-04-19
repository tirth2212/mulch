from fastapi import FastAPI, Request
import subprocess
import json
from datetime import datetime
app = FastAPI()

@app.get("/")
def root():
    return {"status": "server running"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        payload = await request.json()

        # Check for the webhook challenge (used during registration)
        if "challenge" in payload:
            print("🤝 Challenge received from Monday. Returning it...")
            return {"challenge": payload["challenge"]}

        print("📬 Webhook received:")
        print(json.dumps(payload, indent=2))

        # Optional: Trigger your sync job
        subprocess.Popen(["python", "sync_all_data.py"], cwd="../database")
        #give a time stamp
        print(f"✅ Webhook received at {datetime.now()}")
        return {"status": "ok"}

    except Exception as e:
        print(f"❌ Error in webhook: {e}")
        return {"error": str(e)}


