# Energy Spike Prediction System

End-to-end solution for planning medical device manufacturing runs and forecasting
energy spike risk. Operators can schedule production lines, automatically enrich plans
with weather data, and visualise probabilistic spike forecasts across time.

## Project Structure

- `backend/` – FastAPI service providing scheduling endpoints, weather integration, and
  a RandomForest-based spike predictor.
- `frontend/` – Vite/React single-page application for scheduling, monitoring heatmap
  demand, and reviewing probability timelines.
- `backend/synthetic_med_device_energy.csv` – Synthetic dataset used to train the
  predictive model.

## Getting Started

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python train_model.py         # builds/refreshes energy_spike_model.pkl
uvicorn app:app --reload      # starts the FastAPI service on http://127.0.0.1:8000
```

Key endpoints:

- `GET /config` – Lines, device catalogue, and facility metadata for the UI.
- `POST /schedule` – Save a production schedule, enrich with weather data, and return
  spike probabilities.
- `GET /schedules` – Retrieve stored schedules (persisted to `backend/data/schedules.json`).
- `GET /predictions/heatmap` – Aggregated probability heatmap for all schedules.

Weather data is sourced from [open-meteo.com](https://open-meteo.com/) based on the
facility location defined in `app.py`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev         # launches Vite dev server on http://127.0.0.1:5173
```

Set `VITE_API_BASE_URL` in `.env` if the backend is running on a non-default URL.

Production build:

```bash
npm run build
npm run preview
```

### 3. Typical Workflow

1. Train or refresh the model (`python backend/train_model.py`).
2. Run the FastAPI backend (`uvicorn app:app --reload`).
3. Launch the React frontend (`npm run dev`).
4. Use the UI to:
   - Schedule batches by line, device mix, and start time.
   - Flag maintenance, calibration, or unexpected events.
   - Review spike probability timelines and weather context.
   - Monitor high-risk windows via the line/time heatmap.

## Technology Stack

- **Model**: RandomForestClassifier with scikit-learn pipeline, automatically handling
  categorical encoding and median imputation.
- **Backend**: FastAPI, httpx for weather ingestion, joblib for model persistence,
  pandas for feature preparation.
- **Frontend**: React 18, Vite, Axios, Recharts for charting, Day.js for time handling.

## Testing & Validation

- `python backend/train_model.py` – confirm training succeeds and evaluate accuracy.
- `npm run build` – ensure the frontend compiles without errors.

Additional integration, unit, or smoke tests can be added via pytest for the backend
and Vitest/React Testing Library for the frontend as future enhancements.