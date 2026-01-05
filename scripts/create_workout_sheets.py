import pandas as pd
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.worksheet.datavalidation import DataValidation

# Read the existing exercise list
existing_exercises = pd.read_excel('Workout_Inputs.xlsx', sheet_name='Exercise_List')

# Create the new Exercises reference sheet with simplified structure
exercises_df = pd.DataFrame({
    'exercise_id': range(1, len(existing_exercises) + 1),
    'exercise_name': existing_exercises['Exercise'].values,
    'muscle_group': existing_exercises['MuscleGroup'].values,
    'category': existing_exercises['Category'].values
})

# Create Session_Info sheet for workout-level metadata
session_info_df = pd.DataFrame({
    'field': ['workout_date', 'location', 'workout_length'],
    'value': ['2026-01-02', 'Balham FF', '60 mins']
})

# Create the Workout_Input sheet with example data showing both strength and cardio
# Note: distance is in km for all exercises
workout_input_df = pd.DataFrame({
    'exercise_name': ['Bench Press', 'Bench Press', 'Bench Press', 'Pull-Ups', 'Rowing Machine', 'Treadmill'],
    'set': [1, 2, 3, 1, 1, 1],
    'reps': [10, 8, 8, 12, None, None],
    'weight': [60, 70, 70, 0, None, None],
    'time': [None, None, None, None, 15, 20],
    'distance': [None, None, None, None, 3.0, 5.0],  # km for all cardio
    'rpe': [7, 8, 9, 7, 6, 8]
})

# Create Excel file with multiple sheets
with pd.ExcelWriter('Workout_Tracker.xlsx', engine='openpyxl') as writer:
    # Write Session_Info sheet (workout-level data)
    session_info_df.to_excel(writer, sheet_name='Session_Info', index=False)

    # Write Exercises reference sheet
    exercises_df.to_excel(writer, sheet_name='Exercises', index=False)

    # Write Workout_Input sheet (with example data that can be cleared)
    workout_input_df.to_excel(writer, sheet_name='Workout_Input', index=False)

# Now add data validation for the exercise_name column
wb = load_workbook('Workout_Tracker.xlsx')
ws_input = wb['Workout_Input']

# Create a data validation that references the exercise_name column in Exercises sheet
# The formula references cells B2 to B44 (43 exercises + header row)
num_exercises = len(exercises_df)
dv = DataValidation(
    type="list",
    formula1=f"=Exercises!$B$2:$B${num_exercises + 1}",
    allow_blank=False
)
dv.error = 'Please select an exercise from the list'
dv.errorTitle = 'Invalid Exercise'
dv.prompt = 'Select an exercise from the dropdown'
dv.promptTitle = 'Exercise Selection'

# Add the validation to the exercise_name column (column A)
# Apply to 1000 rows to give plenty of room for logging
ws_input.add_data_validation(dv)
dv.add(f'A2:A1000')

wb.save('Workout_Tracker.xlsx')

print("✓ Created Workout_Tracker.xlsx with 3 sheets:")
print(f"  - Session_Info: One-time inputs per workout (date, location, length)")
print(f"  - Exercises: {len(exercises_df)} exercises from your existing list")
print(f"  - Workout_Input: Template with strength + cardio examples")
print(f"  - Added dropdown validation for exercise_name (links to Exercises sheet)")
print("\nWorkflow:")
print("1. Enter workout_date (and location) ONCE in Session_Info")
print("2. Log all exercises in Workout_Input (use dropdown for exercise_name)")
print("3. Python script merges them automatically")
print("\nColumns in Workout_Input:")
print("  • Strength: exercise_name, set, reps, weight (kg), rpe")
print("  • Cardio: exercise_name, set, time (min), distance (km), rpe")
print("  • All distance values are in km")
