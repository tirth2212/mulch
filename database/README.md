# Mulch Database System

A PostgreSQL database system for managing mulch jobs, truck locations, and scheduling data from Monday.com and Verizon Connect.

## Features

- Imports job and scheduling data from Monday.com
- Tracks truck locations from Verizon Connect API
- Provides a centralized data store with proper relationships
- Optimized for geographic queries with PostGIS
- Handles relationships between jobs, trucks, materials, and clients

## Database Schema

The database is structured with the following main tables:

- `jobs` - Job information from Monday.com
- `vehicles` - Vehicle information
- `vehicle_status_history` - Historical vehicle GPS location data
- `job_assignments` - Vehicle schedules and job assignments
- `clients` - Client information
- `materials` - Material types
- `material_vendors` - Material vendors
- `job_types` - Types of jobs (HOA, Hospital, etc.)
- `job_statuses` - Status information for jobs

## Setup

### Prerequisites

- PostgreSQL 12+ with PostGIS extension
- Python 3.9+
- Monday.com API credentials
- Verizon Connect API credentials

### Installation

1. Set up a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Make sure your `.env` file contains the following variables:
   ```
   # Monday API credentials
   MONDAY_API_TOKEN=your_monday_token
   BOARD_ID=your_board_id

   # Verizon Connect API credentials
   VERIZON_USERNAME=your_verizon_username
   VERIZON_PASSWORD=your_verizon_password
   VERIZON_APP_ID=your_verizon_app_id

   # PostgreSQL connection params (will be added by setup_db.py)
   PG_HOST=localhost
   PG_PORT=5432
   PG_DATABASE=mulch
   PG_USER=postgres
   PG_PASSWORD=your_password
   ```

4. Create the database and schema:
   ```
   python setup_db.py
   ```

### Data Import

Run the data synchronization script to import all data:
```
python db_connector.py
```

This script will:
1. Import trucks/vehicles from the defined list
2. Import job data from Monday.com
3. Import vehicle location data from Verizon Connect

## Database Structure

### Main Tables

- `clients`: Stores client information
- `materials`: Contains different material types
- `job_types`: Different categories of jobs
- `job_statuses`: Possible job statuses
- `material_vendors`: Stores material supplier information
- `jobs`: Main job information linked to clients, materials, etc.
- `vehicles`: Truck information
- `vehicle_status_types`: Different status types for vehicles
- `vehicle_status_history`: Historical location data for vehicles
- `job_assignments`: Links jobs to vehicles for scheduling
- `job_schedule`: Scheduled dates and times for jobs

### Spatial Data

This database uses PostGIS to handle location data. Key spatial features:
- Geographic points stored using the `geography` data type
- Automatic conversion of latitude/longitude to PostGIS points
- Spatial indices for fast proximity queries
- Triggers to keep geometries in sync with lat/long values

## Regular Data Synchronization

For regular data synchronization, consider setting up a cron job:

```
# Run data sync every hour
0 * * * * cd /path/to/directory && python db_connector.py >> sync.log 2>&1
```

## License

This project is proprietary software.

## Credits

Created for Mulch operation management. 