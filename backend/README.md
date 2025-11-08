# Backend Service

FastAPI application that exposes scheduling, prediction, and heatmap endpoints for the
energy spike prediction workflow.

## Features

- Auto-trains a RandomForest model (with feature engineering and categorical encoding)
  if `energy_spike_model.pkl` is missing or outdated.
- Persists all scheduled runs to `data/schedules.json` for repeatable insights.
- Fetches external weather data from [open-meteo.com](https://open-meteo.com/) to
  enrich features with temperature, humidity, dew-point, irradiance, and wind.
- Generates time-series spike probabilities and aggregated heatmap data per line.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python train_model.py    # optional warm start (app will auto-train if skipped)
uvicorn app:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## Key Endpoints

- `GET /config` – static metadata (production lines, devices, facility settings).
- `POST /schedule` – accepts a schedule payload, enriches with weather, predicts
  spikes, stores the run, and returns the probability series.
- `GET /schedules` – list of all stored schedules with prediction detail.
- `GET /predictions/heatmap` – aggregated probabilities for heatmap visualisation.
- `GET /health` – lightweight readiness check.

### Schedule Payload Example

```json
{
  "facility_id": "Plant_A",
  "production_line": "Line 1",
  "start_time": "2025-11-08T08:00:00-05:00",
  "duration_minutes": 180,
  "devices": [
    {"product_type": "Stent_Catheter", "quantity": 120, "calibration_event": true},
    {"product_type": "Implant_Device", "quantity": 80, "calibration_event": false}
  ],
  "maintenance_window": false,
  "testing_or_calibration": true,
  "unexpected_event": false
}
```

## Model Utilities

- `ml_utils.py` encapsulates loading, training, and baseline feature templates.
- `train_model.py` trains the pipeline and prints evaluation metrics.

## Data Storage

- Trained model: `energy_spike_model.pkl`
- Scheduled runs: `data/schedules.json`

Both artefacts are generated automatically as part of the workflow.

## Testing

```bash
python train_model.py   # confirms training and prints metrics
```

Add pytest suites for endpoint and feature generation logic as needed.