# iOS Shortcut Setup Guide - "Log Workout"

This guide walks you through building the iOS Shortcut that logs workouts to your Google Sheet.

---

## Prerequisites

1. Apps Script deployed (see `apps_script.js`)
2. You have:
   - Web App URL: `https://script.google.com/macros/s/XXXXX/exec`
   - Secret: Your `WORKOUT_WEBHOOK_SECRET` value

---

## Part 1: Create Variables

Open **Shortcuts** app → tap **+** → name it **"Log Workout"**

### 1.1 Set Up Constants
Add these actions at the top:

1. **Text** → paste your Web App URL → Set Variable: `WebAppURL`
2. **Text** → paste your secret → Set Variable: `Secret`

---

## Part 2: Fetch Exercise List

### 2.1 Get Exercises from Google Sheet
1. **URL** → `WebAppURL`
2. **Get Contents of URL**
   - Method: GET
   - Add Query Item: `secret` = `Secret`
3. **Get Dictionary from Input**
4. **Get Value for Key** → `exercises`
5. **Set Variable**: `ExerciseList`

---

## Part 3: Session Info Prompts

### 3.1 Workout Date
1. **Date** → select "Current Date"
2. **Format Date** → Custom: `yyyy-MM-dd`
3. **Set Variable**: `WorkoutDate`

### 3.2 Location
1. **Choose from Menu**
   - Prompt: "Where are you working out?"
   - Options: `Gym`, `Home`, `Outdoors`, `Other`
2. For "Other": **Ask for Input** (Text)
3. **Set Variable**: `Location`

### 3.3 Workout Length
1. **Ask for Input**
   - Prompt: "Workout length (minutes)"
   - Type: Number
2. **Set Variable**: `WorkoutLength`

### 3.4 Time of Day
1. **Choose from Menu**
   - Prompt: "Time of day"
   - Options: `AM`, `PM`, `Evening`
2. **Set Variable**: `TimeOfDay`

### 3.5 Calories (Optional)
1. **Ask for Input**
   - Prompt: "Calories burned (optional)"
   - Type: Number
   - Default: leave empty
2. **Set Variable**: `Calories`

### 3.6 Comments (Optional)
1. **Ask for Input**
   - Prompt: "Any comments? (optional)"
   - Type: Text
2. **Set Variable**: `Comments`

---

## Part 4: Log Exercise Sets (Loop)

### 4.1 Initialize Empty List
1. **List** → (leave empty)
2. **Set Variable**: `WorkoutRows`

### 4.2 Create Repeat Loop
1. **Repeat**
   - Choose: "Repeat Until"... (we'll use a menu to exit)

Actually, iOS Shortcuts doesn't have a clean "while" loop. Use this pattern:

### Alternative: Repeat Loop with Exit

```
Repeat 50 times:
    ├── Choose Exercise
    ├── Ask for Reps/Weight/etc
    ├── Add to WorkoutRows
    ├── Menu: "Add another set?"
    │     ├── Yes → Continue
    │     └── No → Exit Repeat (Stop this Shortcut... actually use "Nothing")
```

Better approach using **Run Shortcut Recursively** or **Menu-based loop**:

### 4.3 Recommended: Menu Loop Pattern

Use this structure:

```
1. Label: "AddSet"

2. Choose from List → ExerciseList (shows exercise names)
   - Select Key: name
   → Set Variable: SelectedExercise

3. Ask for Input: "Reps" (Number, optional)
   → Set Variable: Reps

4. Ask for Input: "Weight (kg)" (Number, optional)
   → Set Variable: Weight

5. Ask for Input: "Time (minutes)" (Number, optional)
   → Set Variable: Time

6. Ask for Input: "Distance (km)" (Number, optional)
   → Set Variable: Distance

7. Ask for Input: "RPE (1-10)" (Number)
   → Set Variable: RPE

8. Dictionary:
   {
     "exercise_name": SelectedExercise,
     "reps": Reps,
     "weight": Weight,
     "time": Time,
     "distance": Distance,
     "rpe": RPE
   }
   → Set Variable: SetData

9. Add SetData to WorkoutRows
   (Use "Add to Variable" action → WorkoutRows)

10. Choose from Menu: "Add another set?"
    - "Yes" → Run Shortcut (this same shortcut) with input...
              OR use "Repeat" structure
    - "No, I'm done" → Continue to POST
```

### Simpler Alternative: Fixed Repeat

If the recursive approach is confusing:

```
Repeat 30 times:
    1. Choose from Menu: "Add a set?"
       - "Add Set" →
           - Choose exercise
           - Get reps/weight/etc
           - Add to WorkoutRows
       - "Done logging" →
           - Exit Repeat (use "Nothing" action, then If to break)
```

---

## Part 5: Build & Send JSON

### 5.1 Build Session Dictionary
1. **Dictionary**:
```json
{
  "workout_date": WorkoutDate,
  "location": Location,
  "workout_length": WorkoutLength,
  "time_of_day": TimeOfDay,
  "calories": Calories,
  "comments": Comments
}
```
→ Set Variable: `SessionData`

### 5.2 Build Full Payload
1. **Dictionary**:
```json
{
  "session": SessionData,
  "rows": WorkoutRows
}
```
→ Set Variable: `Payload`

### 5.3 POST to Google Sheets
1. **URL**: `WebAppURL`
2. **Get Contents of URL**
   - Method: **POST**
   - Headers: `Content-Type` = `application/json`
   - Add Query Item: `secret` = `Secret`
   - Request Body: **JSON**
   - Body: `Payload`
3. **Get Dictionary from Input**
4. **If** → Get Value for `success` equals `true`
   - **Show Notification**: "Workout logged! [number of sets] sets saved"
5. **Otherwise**
   - **Show Notification**: "Error: [error message]"

---

## Part 6: Add to Home Screen

1. In Shortcuts, tap the **...** on your shortcut
2. Tap the dropdown at top → **Add to Home Screen**
3. Choose an icon (dumbbell recommended)

Optional:
- Add as Widget
- Assign to Action Button (iPhone 15 Pro+)
- Enable for Siri: "Hey Siri, Log Workout"

---

## Quick Reference: JSON Structure

**GET Response** (exercise list):
```json
{
  "success": true,
  "exercises": [
    { "name": "Bench Press", "category": "Push", "muscle_group": "Chest" },
    { "name": "Pull-Ups", "category": "Pull", "muscle_group": "Back" }
  ]
}
```

**POST Request** (your workout):
```json
{
  "session": {
    "workout_date": "2026-01-18",
    "location": "Gym",
    "workout_length": 60,
    "time_of_day": "AM",
    "calories": 450,
    "comments": "Felt strong today"
  },
  "rows": [
    { "exercise_name": "Bench Press", "reps": 10, "weight": 60, "rpe": 7 },
    { "exercise_name": "Bench Press", "reps": 8, "weight": 70, "rpe": 8 }
  ]
}
```

**POST Response**:
```json
{
  "success": true,
  "message": "Logged 2 sets",
  "session_date": "2026-01-18"
}
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Invalid secret" | Check secret matches exactly (no spaces) |
| Exercise list empty | Verify Exercises sheet has data, column is `exercise_name` |
| POST fails | Check JSON structure, ensure all required fields present |
| Shortcut times out | Google Apps Script cold start - try again |
