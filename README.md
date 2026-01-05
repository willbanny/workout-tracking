# Workout Logging & Tracking System

Automated workout data pipeline that extracts data from Google Sheets, processes it, and stores it in a SQLite database.

## Architecture

```
Google Sheets (Input)
        ↓
GitHub Actions (Scheduled)
        ↓
Python ETL Script
        ↓
SQLite Database (workouts.db)
```

## Features

- **Simple Input**: Log workouts in Google Sheets with dropdown validation
- **Automated Processing**: GitHub Actions runs ETL every 24 hours
- **Auto-Clear**: Input sheets cleared after processing (ready for next workout)
- **Historical Data**: Append-only raw data table preserves all history
- **Clean Analytics**: Structured database for querying and analysis

## Google Sheets Structure

### Session_Info
One-time inputs per workout:
- workout_date
- location
- workout_length
- comments

### Exercises (Reference)
43 exercises with:
- exercise_id
- exercise_name
- muscle_group
- category

### Workout_Input
Daily logging (auto-cleared after processing):
- exercise_name (dropdown)
- set
- reps
- weight (kg)
- time (minutes)
- distance (km)
- rpe

## Database Schema

### workout_sets_raw
Append-only table with all historical data

### workout_sets
Clean, upsertable table for analytics

### exercises
Reference table for exercise metadata

## Setup

### 1. Google Cloud Setup
1. Create Google Cloud project
2. Enable Google Sheets API
3. Create service account
4. Download JSON credentials
5. Share Google Sheet with service account email

### 2. GitHub Setup
1. Create GitHub repository
2. Push code to repository
3. Add GitHub Secrets:
   - `SHEET_ID`: Your Google Sheet ID
   - `GOOGLE_CREDENTIALS`: Contents of service account JSON file

### 3. Local Development
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your SHEET_ID
python3 workout_etl.py
```

## Usage

1. **Log Workout**:
   - Open Google Sheets
   - Enter date/location in Session_Info
   - Log exercises in Workout_Input (use dropdowns)

2. **Automatic Processing**:
   - GitHub Actions runs daily at midnight UTC
   - Data extracted, validated, and loaded to database
   - Input sheets cleared for next workout

3. **Manual Run** (optional):
   ```bash
   python3 workout_etl.py
   ```

## Project Structure

```
workout_logging/
├── workout_etl.py              # Main ETL pipeline
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .github/
│   └── workflows/
│       └── workout_etl.yml     # GitHub Actions automation
├── docs/
│   ├── GITHUB_SETUP.md         # Setup instructions
│   └── workout_automation_summary.md  # Project plan
├── scripts/
│   ├── create_workout_sheets.py  # Generate Excel templates
│   ├── migrate_old_data.py       # Migrate historical data
│   └── cleanup_test_data.py      # Cleanup utilities
└── data/
    ├── workouts.db               # SQLite database (tracked)
    ├── Workout_Tracker.xlsx      # Current template
    └── Workout_Inputs.xlsx       # Original data
```

## Automation Schedule

- **Frequency**: Every 24 hours at midnight UTC
- **Manual Trigger**: Available via GitHub Actions UI
- **On Success**: Database updated and committed to repository
