"""
Migration script to import data from old Workout_Inputs.xlsx file
Converts from wide format (Weight_1/Reps_1, etc.) to narrow format (one row per set)
"""

import sqlite3
from datetime import datetime

import pandas as pd


def extract_workout_date(inputs_sheet):
    """Extract workout date from the Inputs sheet"""
    # The date is in the column header
    date_col = inputs_sheet.columns[1]
    if isinstance(date_col, datetime):
        return date_col.strftime('%Y-%m-%d')
    return str(date_col).split()[0]  # fallback


def transform_wide_to_narrow(workout_data, workout_date, location):
    """Transform wide format (Weight_1, Reps_1, etc.) to narrow format (one row per set)"""

    # Filter out rows without exercise names
    workout_data = workout_data[workout_data['Exercise'].notna()].copy()

    rows = []

    for idx, row in workout_data.iterrows():
        exercise_name = row['Exercise']

        # Process up to 4 sets
        for set_num in range(1, 5):
            weight_col = f'Weight_{set_num}'
            reps_col = f'Reps_{set_num}'

            weight = row.get(weight_col)
            reps = row.get(reps_col)

            # Only create a row if we have at least weight OR reps data
            if pd.notna(weight) or pd.notna(reps):
                rows.append({
                    'workout_date': workout_date,
                    'location': location,
                    'exercise_name': exercise_name,
                    'set_number': set_num,
                    'reps': reps if pd.notna(reps) else None,
                    'weight': weight if pd.notna(weight) else None,
                    'time': None,  # Old format didn't track time
                    'distance': None,  # Old format didn't track distance properly
                    'rpe': None,  # Old format didn't have RPE
                })

    return pd.DataFrame(rows)


def load_exercises_from_db():
    """Load exercise reference table from database"""
    conn = sqlite3.connect('workouts.db')
    exercises = pd.read_sql('SELECT exercise_id, exercise_name FROM exercises', conn)
    conn.close()
    return exercises


def enrich_with_exercise_data(workout_data, exercises_df):
    """Join with exercises to get exercise_id and calculate volume"""

    # Join with exercises
    workout_data = workout_data.merge(
        exercises_df,
        on='exercise_name',
        how='left'
    )

    # Calculate volume
    workout_data['volume'] = workout_data['weight'] * workout_data['reps']

    # Add timestamp
    workout_data['created_at'] = datetime.now().isoformat()

    # Check for unmatched exercises
    unmatched = workout_data[workout_data['exercise_id'].isna()]
    if len(unmatched) > 0:
        print(f"\n⚠️  Warning: {len(unmatched)} sets have exercises not in the reference table:")
        for exercise in unmatched['exercise_name'].unique():
            print(f"    - {exercise}")
        print("    These sets will still be imported but won't have an exercise_id")

    return workout_data


def load_to_database(workout_data):
    """Load migrated data to database"""

    conn = sqlite3.connect('workouts.db')

    # Prepare columns for database
    raw_cols = ['workout_date', 'location', 'exercise_id', 'exercise_name',
                'set_number', 'reps', 'weight', 'time', 'distance', 'rpe', 'volume', 'created_at']

    # Add missing columns (muscle_group, category) as None since old data didn't have them
    workout_data['muscle_group'] = None
    workout_data['category'] = None

    # Insert into raw table
    workout_data[raw_cols + ['muscle_group', 'category']].to_sql(
        'workout_sets_raw',
        conn,
        if_exists='append',
        index=False
    )

    print(f"  ✓ Appended {len(workout_data)} sets to workout_sets_raw")

    # Insert into clean table (removing duplicates for same date/exercise/set)
    clean_cols = ['workout_date', 'exercise_id', 'set_number', 'reps', 'weight',
                  'time', 'distance', 'rpe', 'volume']

    # Delete existing records for this workout_date before inserting
    workout_date = workout_data['workout_date'].iloc[0]
    cursor = conn.cursor()
    cursor.execute('DELETE FROM workout_sets WHERE workout_date = ?', (workout_date,))
    print(f"  ✓ Cleared existing data for {workout_date}")

    workout_data[clean_cols].to_sql('workout_sets', conn, if_exists='append', index=False)
    print(f"  ✓ Inserted {len(workout_data)} sets to workout_sets")

    conn.commit()
    conn.close()


def main():
    print("=" * 60)
    print("📦 MIGRATING OLD WORKOUT DATA")
    print("=" * 60)

    # Read old Excel file
    print("\n📥 Reading Workout_Inputs.xlsx...")
    xl = pd.ExcelFile('Workout_Inputs.xlsx')

    inputs_sheet = pd.read_excel(xl, 'Inputs')
    workout_data = pd.read_excel(xl, 'Workout_Inputs')

    # Extract metadata
    workout_date = extract_workout_date(inputs_sheet)
    location = inputs_sheet.iloc[1, 1] if len(inputs_sheet) > 1 else 'Unknown'

    print(f"  ✓ Workout Date: {workout_date}")
    print(f"  ✓ Location: {location}")
    print(f"  ✓ Found {len(workout_data)} rows in old format")

    # Transform wide to narrow
    print("\n🔄 Transforming from wide to narrow format...")
    narrow_data = transform_wide_to_narrow(workout_data, workout_date, location)
    print(f"  ✓ Converted to {len(narrow_data)} sets in narrow format")
    print(f"  ✓ Unique exercises: {narrow_data['exercise_name'].nunique()}")

    # Load exercises and enrich data
    print("\n🔗 Enriching with exercise reference data...")
    exercises = load_exercises_from_db()
    enriched_data = enrich_with_exercise_data(narrow_data, exercises)

    # Show summary
    print("\n📊 Migration Summary:")
    print(f"  Total sets: {len(enriched_data)}")
    print(f"  Exercises with data:")
    exercise_summary = enriched_data.groupby('exercise_name').agg({
        'set_number': 'count',
        'volume': 'sum'
    }).sort_values('volume', ascending=False)

    for exercise, stats in exercise_summary.iterrows():
        volume = f"{stats['volume']:.0f} kg" if pd.notna(stats['volume']) else "N/A"
        print(f"    {exercise}: {int(stats['set_number'])} sets, {volume}")

    # Load to database
    print("\n📤 Loading to database...")
    load_to_database(enriched_data)

    print("\n" + "=" * 60)
    print("✅ Migration completed successfully!")
    print("=" * 60)
    print("\nTo verify, run: python3 workout_etl.py")


if __name__ == "__main__":
    main()
