import requests
import base64
import jwt
# ============================
# CONFIGURATION
# ============================

# Your Reveal Integration User credentials (NOT Developer Portal credentials)
USERNAME = "REST_Truck_Data_4086@1156611.com"
PASSWORD = "Verizon@1234"

    # Your Verizon Connect App ID
APP_ID = "fleetmatics-p-us-cLGH0Rw2WNpPtlk83sWcI9ncHIZ2OpnZUb324VB5"  # Replace with your actual App ID

# API Endpoints
TOKEN_URL = "https://fim.api.us.fleetmatics.com/token"  # Token endpoint
VEHICLES_URL = "https://fim.api.us.fleetmatics.com:443/rad/v1/vehicles/getvehiclesactivedtcs"  # Vehicles endpoint

# ============================
# HELPER FUNCTIONS
# ============================

def get_base64_encoded_credentials(username, password):
    """
    Encodes the username and password in Base64 for Basic Authentication.
    """
    credentials = f"{username}:{password}"
    return base64.b64encode(credentials.encode()).decode()

def get_bearer_token():
    """
    Fetches a Bearer Token using the Base64-encoded Integration User credentials.
    """
    encoded_credentials = get_base64_encoded_credentials(USERNAME, PASSWORD)
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Accept": "application/json"
    }

    response = requests.get(TOKEN_URL, headers=headers)

    # Print raw response for debugging
    print("🔍 Response Status Code for Bearer Token:", response.status_code)
    # print("🔍 Response Text:", response.text)

    if response.status_code == 200:
        access_token = response.text  # Directly extract the token as a string
        print("✅ Successfully retrieved Bearer Token")
        return access_token.strip()  # Remove any unwanted spaces/newlines
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        return None



def get_vehicles(access_token):
    """
    Fetches vehicle location data from Verizon Connect API.
    
    Args:
        access_token: Bearer token for authentication
        
    Returns:
        str: JSON response text with vehicle data, or None on error
    """
    # API Endpoint for vehicle locations
    TEST_URL = "https://fim.api.us.fleetmatics.com:443/rad/v1/vehicles/locations"

    # Headers
    headers = {
        "Accept": "application/json",
        "Authorization": f"Atmosphere atmosphere_app_id={APP_ID}, Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Vehicle IDs to query
    data = ["NS02", "NS05", "NS06", "NS07", "NS08", "NS09", "NS10", "NS21"] 
    
    # Send request
    response = requests.post(TEST_URL, headers=headers, json=data)

    # Debug output
    print("🔍 Response Status Code for Vehicles:", response.status_code)
    print("🔍 Response Text for Vehicles:", response.text)
    
    # Return the response text on success
    if response.status_code == 200:
        return response.text
    else:
        print(f"❌ Error getting vehicle data: {response.status_code} - {response.text}")
        return None


# ============================
# MAIN EXECUTION
# ============================

import json

if __name__ == "__main__":
    access_token = get_bearer_token()

    if access_token:
        vehicles = get_vehicles(access_token)
        if vehicles:
            try:
                data = json.loads(vehicles)
                with open("json/truck_location.json", "w") as f:
                    json.dump(data, f, indent=2)
                print("✅ Saved vehicle data to truck_location.json")
            except json.JSONDecodeError:
                print("❌ Response was not valid JSON.")





