import os
import requests
import json
from dotenv import load_dotenv
from tabulate import tabulate
import time

# 1. Load environment variables (e.g., MONDAY_API_TOKEN)
load_dotenv()

# 2. Basic configs
MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_API_TOKEN = os.getenv("MONDAY_API_TOKEN")

# 3. Your truck boards (board IDs)
TRUCK_BOARDS = {
    "NS02": "8120708467",
    "NS02B": "8120531280",
    "NS05": "8120783462",
    "NS06": "8120798328",
    "NS07": "8120866201",
    "NS08": "8120812895",
    "NS09": "8120843584",
    "NS10": "8120708467",
    "NS21": "8120879886",
    # Add more if needed
}

# 4. Only these two group titles
ALLOWED_GROUP_TITLES = ["Schedule", "Production Review"]

# 5. Mapping Monday column IDs -> Friendly Names
TRUCK_COLUMN_MAPPING = {
    "name": "Name",
    "date4": "Date",
    "status6": "Dispatch Status",
    "status2": "Load Status",
    "numbers3": "Quantity Left on Truck",
    "formula6": "Quantity Installed",
    "mirror6": "Client",
    "connect_boards": "Job Name",
    "mirror3": "Material Vendor",
    "mirror48": "Job Address",
    "mirror62": "Material",
    "mirror8": "Bid Qty",
    "mirror16": "Job Type",
    "formula24": "Job Conversion to Hours",
    "formula2": "Avg Qty Installed / Hour (Job)",
}

# ---------------------------
# Debug helper (optional)
# ---------------------------
DEBUG_MODE = False

def debug_print(title, data):
    """Helper to print debug messages if DEBUG_MODE = True."""
    if DEBUG_MODE:
        print(f"\n--- DEBUG: {title} ---")
        if isinstance(data, (dict, list)):
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(data)

# ---------------------------------------------------
# FETCH FUNCTIONS
# ---------------------------------------------------

def fetch_groups(board_id, api_key):
    """Get all groups for a given board."""
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
    data = response.json()
    if "errors" in data:
        raise Exception(f"fetch_groups Error: {data['errors'][0]['message']}")

    groups_list = data["data"]["boards"][0]["groups"]
    groups_dict = {g["title"]: g["id"] for g in groups_list}
    debug_print(f"Groups for Board {board_id}", groups_dict)
    return groups_dict

def fetch_columns(board_id, api_key):
    """Fetch all columns (id, title, type) for inspection."""
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
    data = response.json()
    if "errors" in data:
        raise Exception(f"fetch_columns Error: {data['errors'][0]['message']}")
    
    columns = data["data"]["boards"][0]["columns"]
    debug_print(f"Columns for Board {board_id}", columns)
    return columns

def fetch_items_paginated(board_id, api_key):
    """
    Fetch all items from the given board using pagination.
    NOTE: We include the necessary fragments to handle mirror & connect columns:
      ... on MirrorValue { display_value }
      ... on BoardRelationValue { linked_item_ids, linked_items { id name } }
    """
    items = []
    cursor = None
    page_num = 0

    while True:
        page_num += 1
        query = f"""
        {{
          boards(ids: [{board_id}]) {{
            items_page(limit: 100{f', cursor: "{cursor}"' if cursor else ''}) {{
              cursor
              items {{
                id
                name
                group {{ id title }}
                column_values {{
                  id
                  text
                  value

                  # Location columns
                  ... on LocationValue {{
                    lat
                    lng
                  }}

                  # Mirror columns
                  ... on MirrorValue {{
                    display_value
                  }}

                  # Connect boards columns
                  ... on BoardRelationValue {{
                    linked_item_ids
                    linked_items {{
                      id
                      name
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
        """
        headers = {"Authorization": api_key}
        response = requests.post(MONDAY_API_URL, json={"query": query}, headers=headers)
        data = response.json()
        
        if "errors" in data:
            raise Exception(f"fetch_items_paginated Error: {data['errors'][0]['message']}")
        
        board_data = data["data"]["boards"][0]
        page_data = board_data["items_page"]
        new_items = page_data["items"]
        items.extend(new_items)

        debug_print(f"Page #{page_num} Items for Board {board_id}", [i["id"] for i in new_items])
        
        cursor = page_data.get("cursor")
        if not cursor:
            break  # no more pages left

    debug_print(f"Total Items Fetched for Board {board_id}", len(items))
    return items

# ---------------------------------------------------
# PARSING FUNCTION
# ---------------------------------------------------

def parse_column_values(column_values):
    """
    Given the list of column_values from Monday's API (with expansions),
    parse them based on TRUCK_COLUMN_MAPPING.

    For mirror/connect boards:
      - MirrorValue:  check 'display_value'
      - BoardRelationValue: check 'linked_items'
    """
    parsed = {}

    for col in column_values:
        col_id = col["id"]
        # Use our mapping if it exists; otherwise skip
        mapped_key = TRUCK_COLUMN_MAPPING.get(col_id)

        if not mapped_key:
            continue  # skip columns we don't care about

        # Normal scenario: .text might have data (like "Awaiting Dispatch" or "2025-04-12")
        # But for mirrors/connect boards, .text can be empty, so let's check expansions
        # We'll build a final 'val' to put in parsed[mapped_key]

        # 1. MirrorValue -> display_value
        if "display_value" in col:
            # This is a mirror column
            val = col.get("display_value") or ""
        # 2. BoardRelationValue -> linked_items
        elif "linked_items" in col:
            # This is a connect boards column
            linked_items = col["linked_items"]
            if linked_items:
                # If multiple linked items, join by comma
                val = ", ".join(item["name"] for item in linked_items)
            else:
                val = ""  # no connected items
        else:
            # fallback: normal columns, location columns, or just text
            val = col.get("text", "")

        parsed[mapped_key] = val

    return parsed

# ---------------------------------------------------
# MAIN SCRIPT
# ---------------------------------------------------
if __name__ == "__main__":
    try:
        print("🚚 Truck Dashboard: Unified Multi-Board Report")

        full_output = []  # Collect all truck board data here

        # Loop over each truck board
        for team_name, board_id in TRUCK_BOARDS.items():
            print(f"\n================= 🛻 {team_name} (Board ID: {board_id}) =================")

            try:
                # 1. Fetch groups
                groups_dict = fetch_groups(board_id, MONDAY_API_TOKEN)

                # 2. Filter only the groups we need
                allowed_groups = {k: v for k, v in groups_dict.items() if k in ALLOWED_GROUP_TITLES}

                # 3. Optionally fetch columns to confirm structure
                fetch_columns(board_id, MONDAY_API_TOKEN)

                # 4. Fetch items (paginated) with expanded fragments
                start_time = time.time()
                MAX_RETRIES = 3
                WAIT_SECONDS = 60

                for attempt in range(MAX_RETRIES):
                    try:
                        all_items = fetch_items_paginated(board_id, MONDAY_API_TOKEN)
                        break
                    except Exception as e:
                        if "Complexity budget exhausted" in str(e):
                            print(f"⚠️ Attempt {attempt+1}/{MAX_RETRIES} failed for {team_name} due to complexity limits.")
                            if attempt < MAX_RETRIES - 1:
                                print(f"🔁 Retrying {team_name} in {WAIT_SECONDS} seconds...")
                                time.sleep(WAIT_SECONDS)
                            else:
                                print(f"❌ Skipping board {team_name} after {MAX_RETRIES} failed attempts.")
                                all_items = []  # prevent crash later
                        else:
                            raise

                end_time = time.time()
                print(f"Time taken to fetch items: {end_time - start_time:.2f} seconds")

                # 5. Filter items by group & parse columns
                grouped_data = {grp_title: [] for grp_title in allowed_groups.keys()}

                for item in all_items:
                    grp_title = item["group"]["title"]
                    if grp_title in allowed_groups:
                        parsed_dict = parse_column_values(item["column_values"])
                        parsed_dict["Name"] = item["name"]
                        grouped_data[grp_title].append(parsed_dict)

                # 6. Print tables and collect data
                for group_title, rows in grouped_data.items():
                    if rows:
                        print(f"\n📦 {team_name} - {group_title}:")
                        all_keys = set()
                        for r in rows:
                            all_keys.update(r.keys())

                        desired_order = ["Name"] + list(TRUCK_COLUMN_MAPPING.values())
                        columns_in_use = [c for c in desired_order if c in all_keys]

                        table_data = []
                        for r in rows:
                            row_data = [r.get(col, "") for col in columns_in_use]
                            table_data.append(row_data)

                        print(tabulate(table_data, headers=columns_in_use, tablefmt="grid"))

                        # Save the data into output structure
                        full_output.append({
                            "vehicle": team_name,
                            "group": group_title,
                            "data": rows
                        })
                    else:
                        print(f"\n🚫 No data in group: {group_title}")

                        # Save the data into output structure
                        full_output.append({
                            "vehicle": team_name,
                            "group": group_title,
                            "data": rows
                        })

            except Exception as e:
                print(f"❌ Error processing board {team_name} (ID {board_id}): {e}")

        # ✅ Save all truck board data to JSON
        with open("json/truck.json", "w") as f:
            json.dump(full_output, f, indent=2)
            print("\n✅ Saved truck board data to truck.json")

    except Exception as global_e:
        print(f"\n❌ Global Error: {global_e}")
