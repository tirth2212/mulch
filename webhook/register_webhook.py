import os
import requests
from dotenv import load_dotenv

load_dotenv()

MONDAY_API_TOKEN = os.getenv("MONDAY_API_TOKEN")
BOARD_ID = os.getenv("BOARD_ID")  # Or hardcode it here
WEBHOOK_URL = "https://143f-2606-8700-d-5-b17b-81e4-e8d6-86d6.ngrok-free.app/webhook"  # Replace with your ngrok HTTPS URL

def register_webhook():
    query = """
    mutation ($board_id: Int!, $url: String!, $event: WebhookEventType!) {
      create_webhook(board_id: $board_id, url: $url, event: $event) {
        id
      }
    }
    """
    variables = {
        "board_id": int(BOARD_ID),
        "url": WEBHOOK_URL,
        "event": "change_column_value"  # Options: create_item, change_column_value, etc.
    }

    headers = {
        "Authorization": MONDAY_API_TOKEN,
        "Content-Type": "application/json"
    }

    response = requests.post(
        url="https://api.monday.com/v2",
        json={"query": query, "variables": variables},
        headers=headers
    )

    print("📬 Webhook registration response:")
    print(response.json())

if __name__ == "__main__":
    register_webhook()

