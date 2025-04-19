import os
import requests
import json
from dotenv import load_dotenv
from tabulate import tabulate
import time

# Load environment variables
load_dotenv()

# Configuration
MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_API_TOKEN = os.getenv("MONDAY_API_TOKEN")
BOARD_ID = os.getenv("BOARD_ID")

COLUMN_MAPPING = {
    'link_to_item1': 'Client',
    'type1': 'Customer Type',
    'sales_rep_0': 'Sales Rep.',
    'location': 'Job Address',
    'dropdown9': 'Job Type',
    'status0': 'Material',
    'connect_boards': 'Material Vendor',
    'depth': 'Depth',
    'numbers3': 'Bid Qty',
    'project': 'Status',
    'file': 'Map',
    'people_mkm352s8': 'People',
    'location_column': 'Latitude/Longitude',
    'check27': 'Night?' 
}

def debug_print(title, data):
    """Helper function for debug output"""
    print(f"\n{title}:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

def fetch_groups(board_id, api_key):
    """Fetch all groups and their IDs"""
    query = f"""
    {{
      boards(ids: [{board_id}]) {{
        groups {{
          id
          title
        }}
      }}
    }}
    """
    headers = {"Authorization": api_key}
    response = requests.post(MONDAY_API_URL, json={"query": query}, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Groups API failed: {response.text}")

    data = response.json()
    if 'errors' in data:
        raise Exception(f"Groups error: {data['errors'][0]['message']}")

    groups = {group['title']: group['id'] for group in data['data']['boards'][0]['groups']}
    return groups

def fetch_all_columns(board_id, api_key):
    """Fetch all columns in the board to inspect available fields"""
    query = f"""
    {{
      boards(ids: [{board_id}]) {{
        columns {{
          id
          title
          type
        }}
      }}
    }}
    """
    headers = {"Authorization": api_key}
    response = requests.post(MONDAY_API_URL, json={"query": query}, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Columns API failed: {response.text}")

    data = response.json()
    columns = data['data']['boards'][0]['columns']
    return columns

def fetch_all_items(board_id, api_key):
    """Fetch all items using pagination"""
    items = []
    cursor = None
    try:
        while True:
            query = f"""
            {{
              boards(ids: [{board_id}]) {{
                items_page(limit: 500{f', cursor: "{cursor}"' if cursor else ''}) {{
                  cursor
                  items {{
                    id
                    name
                    group {{ id title }}
                    column_values {{
                      id
                      text
                      value
                      ... on BoardRelationValue {{
                        linked_item_ids
                        linked_items {{
                          id
                          name
                        }}
                      }}
                      ... on LocationValue {{
                        lat
                        lng
                        address
                      }}
                    }}
                  }}
                }}
              }}
            }}
            """
            headers = {"Authorization": api_key}
            response = requests.post(MONDAY_API_URL, json={"query": query}, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Items API failed: {response.text}")

            data = response.json()
            
            # Check for errors
            if 'errors' in data:
                raise Exception(f"API error: {data['errors'][0]['message']}")
                
            # Handle case where the structure might not be as expected
            if 'data' not in data or 'boards' not in data['data'] or not data['data']['boards']:
                raise Exception("Unexpected API response structure")
                
            board_data = data['data']['boards'][0]
            if 'items_page' not in board_data:
                raise Exception("No items_page in board data")
                
            page_data = board_data['items_page']
            if 'items' not in page_data:
                break
            
            items.extend(page_data['items'])
            
            cursor = page_data.get('cursor')
            if not cursor:
                break  # No more pages left
    except Exception as e:
        # If there's an error, return an empty list and log it
        print(f"Error fetching items: {e}")

    return items

def parse_column_values(column_values):
    """Parse column values, including linked client names and location details"""
    parsed = {}
    for col in column_values:
        if not col:
            continue
        
        col_id = col.get('id')
        if not col_id:
            continue

        if col_id == 'check27':  # Night job status
            try:
                value = col.get('value')
                if value:
                    value_json = json.loads(value)
                    parsed['Night?'] = "✅ Yes" if value_json.get('checked', False) else "❌ No"
                else:
                    parsed['Night?'] = "❌ No"
            except (json.JSONDecodeError, AttributeError):
                parsed['Night?'] = "❌ No"
            continue

        col_name = COLUMN_MAPPING.get(col_id, col_id)

        # Handle linked clients (BoardRelationValue)
        if col_id == 'link_to_item1':
            if col.get('linked_items'):
                parsed[col_name] = col['linked_items'][0].get('name', 'No client linked')
            else:
                parsed[col_name] = "No client linked"
        
        # Handle location column
        elif 'lat' in col and 'lng' in col:
            parsed['Latitude'] = col.get('lat', 'N/A')
            parsed['Longitude'] = col.get('lng', 'N/A')
            parsed['Address'] = col.get('address', 'N/A')
        else:
            parsed[col_name] = col.get('text', '')

    return parsed

# Export the necessary functions
__all__ = ['fetch_groups', 'fetch_all_columns', 'fetch_all_items', 'parse_column_values']

if __name__ == "__main__":
    try:
        print("=== DEBUGGING STARTED ===")

        # 1. Fetch all groups with their IDs
        print("\nStep 1: Fetching groups with IDs...")
        groups = fetch_groups(BOARD_ID, MONDAY_API_TOKEN)

        # print("\nStep 1.5: Fetching all columns...")
        # all_columns = fetch_all_columns(BOARD_ID, MONDAY_API_TOKEN)

        # 2. Fetch all items with pagination
        print("\nStep 2: Fetching all items (paginated)...")
        start_time = time.time()
        all_items = fetch_all_items(BOARD_ID, MONDAY_API_TOKEN)
        end_time = time.time()
        print(f"Time taken to fetch all items: {end_time - start_time} seconds")

        # 3. Categorizing data into separate tables
        print("\nStep 3: Categorizing data into separate tables...")

        categories = {
            "In Progress": [],
            "Paused": [],
            "Jobs to be Scheduled": [],
            "Material Vendors": [],
            "Material Locations": [],
            "Hotels": []
        }

        # Map group titles to categories
        group_to_category = {
            groups.get("In Progress", ""): "In Progress",
            groups.get("Paused", ""): "Paused",
            groups.get("Material Vendor", ""): "Material Vendors",
            groups.get("Material Locations", ""): "Material Locations",
            groups.get("Hotel", ""): "Hotels"
        }

        # Handle "Jobs to be Scheduled" dynamically
        for title, group_id in groups.items():
            if title.startswith("Jobs to be Scheduled"):
                group_to_category[group_id] = "Jobs to be Scheduled"

        # Assign items to appropriate category using group IDs
        for item in all_items:
            group_id = item['group']['id']
            category = group_to_category.get(group_id, None)

            if category:
                parsed = parse_column_values(item['column_values'])
                row = {
                    "Name": item['name'],
                    "Client": parsed.get('Client', 'N/A'),
                    "Status": parsed.get('Status', 'N/A'),
                    "Material": parsed.get('Material', 'N/A'),
                    "Bid Qty": parsed.get('Bid Qty', 'N/A'),
                    "Job Type": parsed.get('Job Type', 'N/A'),
                    "Latitude": parsed.get('Latitude', 'N/A'),
                    "Longitude": parsed.get('Longitude', 'N/A'),
                    "Address": parsed.get('Address', 'N/A'),
                    "Night?": parsed.get('Night?', 'N/A')
                }
                categories[category].append(row)

        # Print separate tables for each category
        for category, data in categories.items():
            if data:
                print(f"\n{category} Jobs:")
                print(tabulate(data, headers="keys", tablefmt="grid"))
            else:
                print(f"\nNo data found for {category}. But group exists!")
        # Save to JSON
        with open("json/api_out.json", "w") as f:
            json.dump(categories, f, indent=2)
        print("✅ Saved job data to api_out.json")

        print("\n=== DEBUGGING COMPLETE ===")

    except Exception as e:
        print(f"\nCritical Error: {e}")
