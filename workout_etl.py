"""
Workout Data ETL Pipeline
Extracts data from Google Sheets, transforms it, and loads into SQLite database
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path

import gspread
import pandas as pd
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# Load environment variables
load_dotenv()

SHEET_ID = os.getenv('SHEET_ID')
CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE')
DB_PATH = 'data/workouts.db'

# Google Sheets scopes
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def get_google_sheets_client():
    """Initialize and return Google Sheets client"""
    # Try to load from environment variable first (for GitHub Actions)
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if creds_json:
        import json
        import base64

        # Decode from base64 (handles all escaping issues)
        try:
            decoded = base64.b64decode(creds_json).decode('utf-8')
            creds_dict = json.loads(decoded)
        except Exception:
            # Fall back to direct JSON if not base64
            creds_dict = json.loads(creds_json)

        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        # Fall back to file for local development
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)

    client = gspread.authorize(creds)
    return client


def extract_from_sheets():
    """Extract data from Google Sheets"""
    print("📥 Extracting data from Google Sheets...")

    client = get_google_sheets_client()
    spreadsheet = client.open_by_key(SHEET_ID)

    # Read all sheets
    session_info = pd.DataFrame(spreadsheet.worksheet('Session_Info').get_all_records())
    exercises = pd.DataFrame(spreadsheet.worksheet('Exercises').get_all_records())
    workout_input = pd.DataFrame(spreadsheet.worksheet('Workout_Input').get_all_records())

    print(f"  ✓ Session_Info: {len(session_info)} fields")
    print(f"  ✓ Exercises: {len(exercises)} exercises")
    print(f"  ✓ Workout_Input: {len(workout_input)} sets logged")

    return session_info, exercises, workout_input


def transform_data(session_info, exercises, workout_input):
    """Transform and clean the data"""
    print("\n🔄 Transforming data...")

    # Convert session_info from vertical to horizontal (field/value pairs)
    session_dict = dict(zip(session_info['field'], session_info['value']))
    workout_date = session_dict.get('workout_date')
    location = session_dict.get('location')
    workout_length = session_dict.get('workout_length')
    comments = session_dict.get('comments', '')

    print(f"  ✓ Workout Date: {workout_date}")
    print(f"  ✓ Location: {location}")

    # Add workout_date to all workout_input rows
    workout_input['workout_date'] = workout_date
    workout_input['location'] = location

    # Join with exercises to get exercise_id and muscle_group
    workout_input = workout_input.merge(
        exercises[['exercise_name', 'exercise_id', 'muscle_group', 'category']],
        on='exercise_name',
        how='left'
    )

    # Replace empty strings with None for numeric columns
    numeric_cols = ['reps', 'weight', 'time', 'distance']
    for col in numeric_cols:
        workout_input[col] = pd.to_numeric(workout_input[col], errors='coerce')

    # Calculate volume (weight × reps) for strength exercises
    workout_input['volume'] = workout_input['weight'] * workout_input['reps']

    # Add timestamp
    workout_input['created_at'] = datetime.now().isoformat()

    # Filter out rows with no exercise_name (empty rows)
    workout_input = workout_input[workout_input['exercise_name'].notna() & (workout_input['exercise_name'] != '')]

    print(f"  ✓ Processed {len(workout_input)} valid sets")
    print(f"  ✓ Calculated volume for strength exercises")

    return workout_input, session_dict


def initialize_database():
    """Create database schema if it doesn't exist"""
    print("\n🗄️  Initializing database...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create exercises reference table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            exercise_id INTEGER PRIMARY KEY,
            exercise_name TEXT UNIQUE NOT NULL,
            muscle_group TEXT,
            category TEXT
        )
    ''')

    # Create raw workout sets table (append-only)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_sets_raw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_date TEXT NOT NULL,
            location TEXT,
            exercise_id INTEGER,
            exercise_name TEXT,
            muscle_group TEXT,
            category TEXT,
            set_number INTEGER,
            reps REAL,
            weight REAL,
            time REAL,
            distance REAL,
            rpe INTEGER,
            volume REAL,
            created_at TEXT,
            FOREIGN KEY (exercise_id) REFERENCES exercises(exercise_id)
        )
    ''')

    # Create clean workout sets table (upsertable)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workout_sets (
            workout_date TEXT NOT NULL,
            exercise_id INTEGER,
            set_number INTEGER,
            reps REAL,
            weight REAL,
            time REAL,
            distance REAL,
            rpe INTEGER,
            volume REAL,
            PRIMARY KEY (workout_date, exercise_id, set_number),
            FOREIGN KEY (exercise_id) REFERENCES exercises(exercise_id)
        )
    ''')

    conn.commit()
    conn.close()

    print("  ✓ Database schema created/verified")


def load_to_database(workout_data, exercises_df):
    """Load data into SQLite database"""
    print("\n📤 Loading data to database...")

    conn = sqlite3.connect(DB_PATH)

    # Upsert exercises (insert or ignore if already exists)
    exercises_df.to_sql('exercises', conn, if_exists='replace', index=False)
    print(f"  ✓ Loaded {len(exercises_df)} exercises to reference table")

    # Rename 'set' column to 'set_number' for database compatibility
    workout_data = workout_data.rename(columns={'set': 'set_number'})

    # Append to raw table (always insert)
    raw_cols = ['workout_date', 'location', 'exercise_id', 'exercise_name', 'muscle_group',
                'category', 'set_number', 'reps', 'weight', 'time', 'distance', 'rpe', 'volume', 'created_at']
    workout_data[raw_cols].to_sql('workout_sets_raw', conn, if_exists='append', index=False)
    print(f"  ✓ Appended {len(workout_data)} sets to raw table")

    # Upsert to clean table (replace if date/exercise/set already exists)
    clean_cols = ['workout_date', 'exercise_id', 'set_number', 'reps', 'weight', 'time', 'distance', 'rpe', 'volume']

    # Delete existing records for this workout_date before inserting
    workout_date = workout_data['workout_date'].iloc[0]
    cursor = conn.cursor()
    cursor.execute('DELETE FROM workout_sets WHERE workout_date = ?', (workout_date,))

    workout_data[clean_cols].to_sql('workout_sets', conn, if_exists='append', index=False)
    print(f"  ✓ Upserted {len(workout_data)} sets to clean table")

    conn.commit()
    conn.close()


def clear_input_sheets():
    """Clear Workout_Input sheet after successful processing"""
    print("\n🧹 Clearing input sheets for next workout...")

    client = get_google_sheets_client()
    spreadsheet = client.open_by_key(SHEET_ID)

    # Clear Workout_Input sheet (keep header row)
    workout_sheet = spreadsheet.worksheet('Workout_Input')

    # Get all values to check how many rows exist
    all_values = workout_sheet.get_all_values()

    if len(all_values) > 1:  # If there's data beyond the header
        # Clear everything except the header row (row 1)
        # Data validation is tied to the range, so it will persist
        workout_sheet.batch_clear(['A2:Z1000'])
        print(f"  ✓ Cleared {len(all_values) - 1} rows from Workout_Input")
    else:
        print("  ✓ Workout_Input already empty")

    # Reset Session_Info values (but keep structure)
    session_sheet = spreadsheet.worksheet('Session_Info')

    # Update the 'value' column to be empty, preparing for next workout
    session_sheet.update(values=[[''], [''], [''], ['']], range_name='B2:B5')
    print("  ✓ Reset Session_Info values for next workout")


def generate_summary_report():
    """Generate a summary of what's in the database"""
    print("\n📊 Database Summary:")

    conn = sqlite3.connect(DB_PATH)

    # Total sets
    total_sets = pd.read_sql_query('SELECT COUNT(*) as count FROM workout_sets_raw', conn).iloc[0]['count']
    print(f"  Total sets logged: {total_sets}")

    # Unique workout dates
    unique_dates = pd.read_sql_query('SELECT COUNT(DISTINCT workout_date) as count FROM workout_sets_raw', conn).iloc[0]['count']
    print(f"  Unique workout dates: {unique_dates}")

    # Total volume by muscle group
    volume_by_muscle = pd.read_sql_query('''
        SELECT muscle_group, SUM(volume) as total_volume
        FROM workout_sets_raw
        WHERE volume IS NOT NULL
        GROUP BY muscle_group
        ORDER BY total_volume DESC
        LIMIT 5
    ''', conn)

    print("\n  Top 5 muscle groups by volume:")
    for _, row in volume_by_muscle.iterrows():
        print(f"    {row['muscle_group']}: {row['total_volume']:.0f} kg")

    conn.close()


def main():
    """Main ETL pipeline"""
    print("=" * 60)
    print("🏋️  WORKOUT DATA ETL PIPELINE")
    print("=" * 60)

    try:
        # Initialize database
        initialize_database()

        # EXTRACT
        session_info, exercises, workout_input = extract_from_sheets()

        # TRANSFORM
        transformed_data, session_dict = transform_data(session_info, exercises, workout_input)

        # LOAD
        load_to_database(transformed_data, exercises)

        # CLEAR INPUT SHEETS (prepare for next workout)
        clear_input_sheets()

        # REPORT
        generate_summary_report()

        print("\n" + "=" * 60)
        print("✅ ETL pipeline completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
