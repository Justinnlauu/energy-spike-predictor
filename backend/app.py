from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import joblib
from fastapi.middleware.cors import CORSMiddleware

# Load your trained XGBoost model
model = joblib.load("energy_spike_model.pkl")

app = FastAPI(title="Energy Spike Predictor API")

# Allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define input schema for API
class EnergyInput(BaseModel):
    outdoor_temp_C: float
    outdoor_humidity_pct: float
    dew_point_C: float
    solar_irradiance_Wm2: float
    wind_speed_mps: float
    forecast_temp_next1h: float
    forecast_humidity_next1h: float
    shift_id: int
    hour_of_day: int
    day_of_week: int
    maintenance_flag: int
    post_maintenance_startup: int
    cleanroom_occupancy_count: int
    cleanroom_temp_C: float
    cleanroom_humidity_pct: float
    temp_diff_C: float
    humidity_diff_pct: float
    hvac_fan_speed_pct: float
    chiller_load_pct: float
    autoclave_cycle_active: int
    compressor_count_running: int

@app.post("/predict_spike")
def predict_spike(data: EnergyInput):
    df = pd.DataFrame([data.dict()])
    pred = model.predict(df)[0]
    prob = model.predict_proba(df)[0][1]
    return {"spike_prediction": int(pred), "probability": prob}
