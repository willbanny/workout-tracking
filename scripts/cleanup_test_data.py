"""
Cleanup script to remove test/example data from the database
Keeps only the real migrated workout data
"""

import sqlite3
import pandas as pd


def main():
    print("=" * 60)
    print("🧹 CLEANING UP TEST DATA")
    print("=" * 60)

    conn = sqlite3.connect('../data/workouts.db')

    # Show what we're about to delete
    print("\n📋 Test data to be deleted (from first ETL test run):")
    test_data = pd.read_sql("""
        SELECT id, workout_date, exercise_name, set_number, reps, weight, volume
        FROM workout_sets_raw
        WHERE created_at = '2026-01-05T21:50:11.530202'
        ORDER BY id
    """, conn)

    if len(test_data) == 0:
        print("  ✓ No test data found - database is already clean!")
        conn.close()
        return

    print(test_data.to_string(index=False))
    print(f"\n  Total: {len(test_data)} test sets")

    # Delete the test data
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM workout_sets_raw
        WHERE created_at = '2026-01-05T21:50:11.530202'
    """)

    deleted_count = cursor.rowcount
    conn.commit()

    print(f"\n✅ Deleted {deleted_count} test records from workout_sets_raw")

    # Show updated summary
    print("\n📊 Updated Database Summary:")
    total_sets = pd.read_sql('SELECT COUNT(*) as count FROM workout_sets_raw', conn).iloc[0]['count']
    print(f"  Total sets in raw table: {total_sets}")

    volume_summary = pd.read_sql("""
        SELECT exercise_name, COUNT(*) as sets, SUM(volume) as total_volume
        FROM workout_sets_raw
        WHERE volume IS NOT NULL
        GROUP BY exercise_name
        ORDER BY total_volume DESC
        LIMIT 5
    """, conn)

    print("\n  Top 5 exercises by volume:")
    for _, row in volume_summary.iterrows():
        print(f"    {row['exercise_name']}: {int(row['sets'])} sets, {row['total_volume']:.0f} kg")

    conn.close()

    print("\n" + "=" * 60)
    print("✅ Cleanup completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
