# Workout Data Automation – Project Summary

## Goal
Create a **low-friction workout logging system** where workouts are entered once into Google Sheets, then automatically cleaned, normalised, aggregated, and stored in a database using Python and free scheduling tools.

Sheets are for **input only**. Python + database handle all logic.

---

## Core Principles
- One simple input sheet
- No formulas or manual aggregation in Sheets
- Append-only raw data
- Reproducible, automated transformations
- Fully free tooling

---

## Architecture Overview
```
Google Sheets (Input)
        ↓
Python ETL Script
        ↓
Local Database (SQLite or DuckDB)
        ↓
Clean + Aggregated Tables
        ↓
(Optional) Output back to Google Sheets / Dashboards
```

---

## Google Sheets Design

### 1. Exercises (Static Reference)
Used as a lookup table.

**Columns**
- exercise_id
- exercise_name
- muscle_group
- equipment
- is_compound

---

### 2. Workout_Input (Daily Use)
The only sheet manually edited.

**Columns**
- workout_date
- exercise_name
- set
- reps
- weight
- rpe

No totals, formulas, or derived fields.

---

## Database Design

### Raw Table (Append-only)
**workout_sets_raw**
- workout_date
- exercise_id
- set
- reps
- weight
- rpe
- created_at

### Clean Fact Table
**workout_sets**
- workout_date
- exercise_id
- reps
- weight
- volume
- rpe

### Aggregated Tables (Derived)
- exercise_daily_volume
- muscle_group_weekly_volume
- estimated_1rm
- rolling_7d_volume

---

## Python Responsibilities

### Extract
- Read Google Sheets using service account
- Load into pandas DataFrames

### Transform
- Join exercises → exercise_id
- Enforce data types
- Remove invalid / duplicate rows
- Calculate derived metrics (e.g. volume)
- Generate workout_id if needed

### Load
- Append raw data
- Upsert clean tables
- Rebuild aggregated tables

---

## Automation & Scheduling

### Preferred Option: GitHub Actions
- Runs Python script on a schedule (e.g. every 6 hours)
- Free for personal use
- Secrets store Google credentials

Alternative:
- Manual execution during early iteration
- Cloud Functions later if needed

---

## Optional Enhancements
- Auto-clear processed rows from input sheet
- Write aggregated results back to Sheets
- PR detection & alerts
- Progressive overload tracking
- Simple dashboards (Sheets / BI later)

---

## Deliverables
- Google Sheet (Exercises + Workout_Input)
- Python ETL script
- SQLite or DuckDB database
- Scheduled automation
- Clean, extensible data model

---

**Outcome:**  
Log workouts fast, once. Never maintain formulas. Get clean, historical, analysable training data forever.
