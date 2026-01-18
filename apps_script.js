/**
 * Google Apps Script - Workout Logging Web App
 *
 * Endpoints:
 *   GET  ?secret=XXX           → Returns exercise list for iOS Shortcut dropdown
 *   POST ?secret=XXX + JSON    → Writes session info and workout sets to sheets
 *
 * Setup:
 *   1. Open your Google Sheet → Extensions → Apps Script
 *   2. Paste this code
 *   3. Add Script Property: WORKOUT_WEBHOOK_SECRET = <your-secret>
 *   4. Deploy → New Deployment → Web App → Execute as Me → Anyone can access
 *   5. Copy the Web App URL for your iOS Shortcut
 */

// Sheet names (adjust if yours differ)
const SESSION_SHEET = 'Session_Info';
const EXERCISES_SHEET = 'Exercises';
const WORKOUT_SHEET = 'Workout_Input';

// Session fields in order (must match your Session_Info 'field' column)
const SESSION_FIELDS = [
  'workout_date',
  'location',
  'workout_length',
  'comments',
  'calories',
  'time_of_day'
];

/**
 * Parse CSV rows into array of objects
 * Format: exercise_name,reps,weight,time,distance,rpe
 * Handles both literal \n and actual newlines, plus \r carriage returns
 */
function parseCSVRows(csvText) {
  const rows = [];

  // Clean the input - handle various newline formats
  let cleaned = csvText || '';

  // Remove carriage returns (both literal \r and actual)
  cleaned = cleaned.replace(/\\r/g, '');
  cleaned = cleaned.replace(/\r/g, '');

  // Normalize newlines - convert literal \n to actual newlines
  cleaned = cleaned.replace(/\\n/g, '\n');

  // Trim leading/trailing whitespace and newlines
  cleaned = cleaned.trim();

  // Split by newlines
  const lines = cleaned.split('\n');

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue; // skip empty lines

    const parts = trimmed.split(',');
    if (parts.length >= 1 && parts[0]) {
      rows.push({
        exercise_name: parts[0] || '',
        reps: parts[1] || '',
        weight: parts[2] || '',
        time: parts[3] || '',
        distance: parts[4] || '',
        rpe: parts[5] || ''
      });
    }
  }

  return rows;
}

/**
 * Derive time_of_day from datetime string
 */
function getTimeOfDay(datetimeStr) {
  if (!datetimeStr) return '';

  // Expected format: "yyyy-MM-dd HH:mm"
  const parts = datetimeStr.split(' ');
  if (parts.length < 2) return '';

  const timePart = parts[1];
  const hour = parseInt(timePart.split(':')[0], 10);

  if (hour < 12) return 'AM';
  if (hour < 17) return 'PM';
  return 'Evening';
}

/**
 * Handle GET requests - return exercise list for dropdown
 */
function doGet(e) {
  // Validate secret
  const secret = e.parameter.secret;
  const expectedSecret = PropertiesService.getScriptProperties().getProperty('WORKOUT_WEBHOOK_SECRET');

  if (!secret || secret !== expectedSecret) {
    return ContentService.createTextOutput(JSON.stringify({ error: 'Invalid secret' }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const exercisesSheet = ss.getSheetByName(EXERCISES_SHEET);

    // Get all exercise data (skip header row)
    const data = exercisesSheet.getDataRange().getValues();
    const headers = data[0];
    const exercises = [];

    // Find column indices
    const nameIdx = headers.indexOf('exercise_name');
    const categoryIdx = headers.indexOf('category');
    const muscleIdx = headers.indexOf('muscle_group');

    // Build exercise list
    for (let i = 1; i < data.length; i++) {
      const row = data[i];
      if (row[nameIdx]) {
        exercises.push({
          name: row[nameIdx],
          category: row[categoryIdx] || '',
          muscle_group: row[muscleIdx] || ''
        });
      }
    }

    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      exercises: exercises
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      error: error.message
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Handle POST requests - write workout data to sheets
 *
 * Expected JSON body (from iOS Shortcut):
 * {
 *   "session": {
 *     "workout_datetime": "2026-01-18 14:30",
 *     "location": "Gym",
 *     "workout_length": 60,
 *     "comments": "Great session",
 *     "calories": 500
 *   },
 *   "rows_csv": "Bench Press,10,60,,,7\nPull-ups,8,0,,,6"
 * }
 */
function doPost(e) {
  // Validate secret
  const secret = e.parameter.secret;
  const expectedSecret = PropertiesService.getScriptProperties().getProperty('WORKOUT_WEBHOOK_SECRET');

  if (!secret || secret !== expectedSecret) {
    return ContentService.createTextOutput(JSON.stringify({ error: 'Invalid secret' }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  try {
    // Sanitize input - escape control characters that break JSON parsing
    let rawBody = e.postData.contents || '';

    // Replace actual newlines, carriage returns, tabs with escaped versions
    rawBody = rawBody.replace(/\r\n/g, '\\n');
    rawBody = rawBody.replace(/\r/g, '\\n');
    rawBody = rawBody.replace(/\n/g, '\\n');
    rawBody = rawBody.replace(/\t/g, '\\t');

    const payload = JSON.parse(rawBody);
    const session = payload.session || {};

    // Handle rows as CSV or JSON array
    let rows = [];
    if (payload.rows_csv) {
      rows = parseCSVRows(payload.rows_csv);
    } else if (payload.rows) {
      rows = payload.rows;
    }

    if (rows.length === 0) {
      return ContentService.createTextOutput(JSON.stringify({
        error: 'No workout rows provided'
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // Derive workout_date and time_of_day from workout_datetime
    if (session.workout_datetime) {
      const parts = session.workout_datetime.split(' ');
      session.workout_date = parts[0] || '';
      session.time_of_day = getTimeOfDay(session.workout_datetime);
    }

    const ss = SpreadsheetApp.getActiveSpreadsheet();

    // Write session info
    writeSessionInfo(ss, session);

    // Write workout rows
    writeWorkoutRows(ss, rows);

    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      message: `Logged ${rows.length} sets`,
      session_date: session.workout_date
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      error: error.message
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Write session metadata to Session_Info sheet
 * Format: Column A = field name, Column B = value
 */
function writeSessionInfo(ss, session) {
  const sheet = ss.getSheetByName(SESSION_SHEET);

  // Clear existing values (column B, rows 2 onwards)
  const lastRow = Math.max(sheet.getLastRow(), SESSION_FIELDS.length + 1);
  if (lastRow > 1) {
    sheet.getRange(2, 2, lastRow - 1, 1).clearContent();
  }

  // Ensure field names exist in column A and write values to column B
  const values = SESSION_FIELDS.map(field => [field, session[field] || '']);
  sheet.getRange(2, 1, SESSION_FIELDS.length, 2).setValues(values);
}

/**
 * Write workout sets to Workout_Input sheet
 * Columns: exercise_name, reps, weight, time, distance, rpe
 */
function writeWorkoutRows(ss, rows) {
  const sheet = ss.getSheetByName(WORKOUT_SHEET);

  // Clear existing data (keep header row)
  const lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    sheet.getRange(2, 1, lastRow - 1, 6).clearContent();
  }

  // Prepare data rows
  const data = rows.map(row => [
    row.exercise_name || '',
    row.reps || '',
    row.weight || '',
    row.time || '',
    row.distance || '',
    row.rpe || ''
  ]);

  // Write all rows at once
  if (data.length > 0) {
    sheet.getRange(2, 1, data.length, 6).setValues(data);
  }
}

/**
 * Test function - run this in Apps Script editor to verify setup
 */
function testSetup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // Check sheets exist
  const sheets = [SESSION_SHEET, EXERCISES_SHEET, WORKOUT_SHEET];
  sheets.forEach(name => {
    const sheet = ss.getSheetByName(name);
    if (sheet) {
      Logger.log(`✓ Found sheet: ${name}`);
    } else {
      Logger.log(`✗ Missing sheet: ${name}`);
    }
  });

  // Check secret is configured
  const secret = PropertiesService.getScriptProperties().getProperty('WORKOUT_WEBHOOK_SECRET');
  if (secret) {
    Logger.log(`✓ Secret configured (length: ${secret.length})`);
  } else {
    Logger.log('✗ Secret not configured - add WORKOUT_WEBHOOK_SECRET to Script Properties');
  }

  // Count exercises
  const exercisesSheet = ss.getSheetByName(EXERCISES_SHEET);
  if (exercisesSheet) {
    const count = exercisesSheet.getLastRow() - 1;
    Logger.log(`✓ Exercises count: ${count}`);
  }
}
