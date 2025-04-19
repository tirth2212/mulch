import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_PARAMS = {
    'host': os.getenv("PG_HOST"),
    'port': os.getenv("PG_PORT"),
    'dbname': os.getenv("PG_DATABASE"),
    'user': os.getenv("PG_USER"),
    'password': os.getenv("PG_PASSWORD")
}

def create_tables():
    commands = [
        """
        CREATE TABLE IF NOT EXISTS clients (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS materials (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS material_vendors (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS job_types (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS job_statuses (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id SERIAL PRIMARY KEY,
            monday_id TEXT UNIQUE,
            name TEXT,
            client_id INT REFERENCES clients(id),
            status_id INT REFERENCES job_statuses(id),
            material_id INT REFERENCES materials(id),
            vendor_id INT REFERENCES material_vendors(id),
            job_type_id INT REFERENCES job_types(id),
            address TEXT,
            latitude FLOAT,
            longitude FLOAT,
            bid_qty FLOAT,
            is_night_job BOOLEAN
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS vehicles (
            id SERIAL PRIMARY KEY,
            code TEXT UNIQUE,
            name TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS vehicle_status_history (
            id SERIAL PRIMARY KEY,
            vehicle_id INT REFERENCES vehicles(id),
            timestamp TIMESTAMPTZ,
            status TEXT,
            address TEXT,
            latitude FLOAT,
            longitude FLOAT,
            speed FLOAT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS job_assignments (
            id SERIAL PRIMARY KEY,
            job_id INT REFERENCES jobs(id),
            vehicle_id INT REFERENCES vehicles(id),
            date DATE,
            dispatch_status TEXT,
            load_status TEXT,
            qty_left FLOAT,
            qty_installed FLOAT
        )
        """
    ]

    with psycopg2.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            for command in commands:
                cur.execute(command)
        conn.commit()
        print("✅ Database schema created successfully.")

if __name__ == "__main__":
    create_tables()
