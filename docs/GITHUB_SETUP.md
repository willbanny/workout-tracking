# GitHub Actions Setup Guide

Follow these steps to set up automated workout data processing.

## Prerequisites

✅ Google Sheets created and shared with service account
✅ Service account JSON file downloaded
✅ ETL script tested locally

## Step 1: Initialize Git Repository (if not done)

```bash
cd /home/willbanny/code/will_projects/workout_logging
git init
git add .
git commit -m "Initial commit: Workout tracking automation"
```

## Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository named `workout-tracking` (or your preferred name)
3. **Do NOT** initialize with README, .gitignore, or license (we have them locally)
4. Click "Create repository"

## Step 3: Push Code to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/workout-tracking.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

## Step 4: Add GitHub Secrets

GitHub Secrets store sensitive credentials securely. The workflow will access them without exposing them in code.

### 4a. Add SHEET_ID Secret

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `SHEET_ID`
5. Value: Your Google Sheet ID (from the .env file)
   ```
   1uOjj2855nHjv7jbTpec5gwuTFNtgPR6ngGW80J6n6js
   ```
6. Click **Add secret**

### 4b. Add GOOGLE_CREDENTIALS Secret

1. Click **New repository secret** again
2. Name: `GOOGLE_CREDENTIALS`
3. Value: **Full contents** of your service account JSON file
   - Open `workout-tracker-483421-70f71dc1ae7b.json`
   - Copy ALL the text (including { and })
   - Paste it into the secret value field
4. Click **Add secret**

The JSON should look like:
```json
{
  "type": "service_account",
  "project_id": "workout-tracker-...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  ...
}
```

## Step 5: Verify Workflow File

The workflow file should already be in your repository:
- `.github/workflows/workout_etl.yml`

If you pushed the code, it's already there. You can verify by:
1. Go to your repository on GitHub
2. Navigate to **Actions** tab
3. You should see "Workout ETL Pipeline" listed

## Step 6: Test the Workflow

### Manual Test (Recommended First)

1. Go to **Actions** tab
2. Click on "Workout ETL Pipeline"
3. Click **Run workflow** dropdown (right side)
4. Click **Run workflow** button
5. Watch it run (takes ~30 seconds)

If successful, you'll see:
- ✅ All steps green
- Database file updated in repository
- New commit with message like "Update workout database - 2026-01-05 22:00"

### Check Scheduled Runs

The workflow will now run automatically every 24 hours at midnight UTC.

To see when it last ran:
- Go to **Actions** tab
- Look for automated runs (they'll have a clock icon ⏰)

## Step 7: Workflow

### Normal Usage:

1. **Log workout in Google Sheets** (anytime during the day)
   - Enter date/location in Session_Info
   - Log exercises in Workout_Input

2. **Wait for automation** (midnight UTC) OR manually trigger
   - GitHub Actions runs ETL
   - Data extracted and saved to database
   - Sheets cleared for next workout

3. **Database updates automatically**
   - New commit appears in repository
   - workouts.db file updated with latest data

## Troubleshooting

### Workflow fails with "Authentication error"
- Check that GOOGLE_CREDENTIALS secret contains the full JSON
- Verify the service account has Editor access to the Google Sheet

### Workflow fails with "Sheet not found"
- Verify SHEET_ID is correct
- Check that the sheet names match exactly: Session_Info, Exercises, Workout_Input

### Database not updating
- Check the Actions tab for error messages
- Verify the workflow has permission to push to the repository

### Manual test
You can always run the ETL locally to test:
```bash
python3 workout_etl.py
```

## Advanced: Change Schedule

To run more or less frequently, edit `.github/workflows/workout_etl.yml`:

```yaml
schedule:
  - cron: '0 0 * * *'    # Midnight daily (current)
  - cron: '0 */6 * * *'  # Every 6 hours
  - cron: '0 */12 * * *' # Every 12 hours
  - cron: '0 0 * * 0'    # Weekly (Sunday midnight)
```

Cron format: `minute hour day month day-of-week`

## Success!

Your workout tracking system is now fully automated! 🎉

Every 24 hours:
- ✅ Data extracted from Google Sheets
- ✅ Validated and transformed
- ✅ Loaded to database
- ✅ Sheets cleared for next workout
- ✅ Database committed to GitHub
