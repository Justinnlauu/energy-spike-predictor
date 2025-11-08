from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from ml_utils import ModelLoadError, load_model_artifacts


app = FastAPI(title="Energy Spike Prediction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Static facility and production configuration
# ---------------------------------------------------------------------------
LINE_OPTIONS = [
    {"id": "Line_01", "label": "Line 1"},
    {"id": "Line_02", "label": "Line 2"},
]

LINE_LABEL_TO_ID = {item["label"]: item["id"] for item in LINE_OPTIONS}
LINE_ID_TO_LABEL = {item["id"]: item["label"] for item in LINE_OPTIONS}

DEVICE_PROFILES: Dict[str, Dict[str, Any]] = {
    "Stent_Catheter": {
        "display_name": "Stent Catheter",
        "sterilization_required": True,
        "hvac_factor": 0.22,
        "compressed_air_factor": 0.18,
        "occupancy_per_unit": 0.12,
        "description": "Invasive device requiring sterilization and strict environmental control.",
    },
    "Catheter_Tube": {
        "display_name": "Catheter Tube",
        "sterilization_required": False,
        "hvac_factor": 0.15,
        "compressed_air_factor": 0.10,
        "occupancy_per_unit": 0.09,
        "description": "Continuous extrusion process with consistent HVAC demand.",
    },
    "Implant_Device": {
        "display_name": "Implant Device",
        "sterilization_required": True,
        "hvac_factor": 0.25,
        "compressed_air_factor": 0.20,
        "occupancy_per_unit": 0.14,
        "description": "High-value implants with rigorous sterilization and validation steps.",
    },
}

FACILITIES: Dict[str, Dict[str, Any]] = {
    "Plant_A": {
        "id": "Plant_A",
        "name": "Boston Medical Device Campus",
        "latitude": 42.361145,
        "longitude": -71.057083,
        "timezone": "America/New_York",
    }
}

WEATHER_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
WEATHER_PARAMETERS = ",".join(
    [
        "temperature_2m",
        "relative_humidity_2m",
        "dewpoint_2m",
        "direct_normal_irradiance",
        "wind_speed_10m",
    ]
)

SERIES_INTERVAL_MINUTES = 30

SCHEDULES_PATH = Path(__file__).resolve().parent / "data" / "schedules.json"
SCHEDULES_PATH.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Model artifacts
# ---------------------------------------------------------------------------
try:
    MODEL_ARTIFACTS = load_model_artifacts()
except ModelLoadError as exc:
    raise RuntimeError(f"Unable to initialise model artifacts: {exc}") from exc

MODEL_PIPELINE = MODEL_ARTIFACTS["model"]
FEATURE_COLUMNS: List[str] = list(MODEL_ARTIFACTS["feature_columns"])
BASELINE_TEMPLATE: Dict[str, Any] = dict(MODEL_ARTIFACTS["baseline_row"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class DeviceQuantity(BaseModel):
    product_type: str = Field(..., description="Device type (matches training data categories).")
    quantity: int = Field(..., gt=0, description="Planned production quantity.")
    sterilization_override: Optional[bool] = Field(
        None, description="Override default sterilization requirement if needed."
    )
    calibration_event: bool = Field(
        False, description="Flag if this device run includes maintenance/calibration activity."
    )

    @validator("product_type")
    def validate_product_type(cls, value: str) -> str:
        if value not in DEVICE_PROFILES:
            raise ValueError(f"Unsupported product_type '{value}'.")
        return value


class ScheduleRequest(BaseModel):
    facility_id: str = Field("Plant_A", description="Facility identifier.")
    production_line: str = Field(..., description="Human-friendly production line label (e.g. 'Line 1').")
    devices: List[DeviceQuantity]
    start_time: datetime = Field(..., description="Scheduled start time in ISO format.")
    duration_minutes: int = Field(120, ge=30, le=24 * 60, description="Planned run duration in minutes.")
    maintenance_window: bool = Field(
        False, description="Whether maintenance/testing is planned during this run."
    )
    testing_or_calibration: bool = Field(
        False, description="Set if calibration or validation activities immediately follow maintenance."
    )
    unexpected_event: bool = Field(
        False, description="Flag unplanned demand or process events increasing spike risk."
    )

    @validator("production_line")
    def validate_line(cls, value: str) -> str:
        if value not in LINE_LABEL_TO_ID:
            raise ValueError(f"Unsupported production_line '{value}'.")
        return value

    @validator("devices")
    def validate_devices(cls, value: List[DeviceQuantity]) -> List[DeviceQuantity]:
        if not value:
            raise ValueError("At least one device entry is required.")
        return value

    @validator("facility_id")
    def validate_facility(cls, value: str) -> str:
        if value not in FACILITIES:
            raise ValueError(f"Unsupported facility_id '{value}'.")
        return value


class WeatherSnapshot(BaseModel):
    temperature_c: float
    humidity_pct: float
    dew_point_c: float
    solar_irradiance_wm2: float
    wind_speed_mps: float


class ProbabilityPoint(BaseModel):
    timestamp: datetime
    probability: float
    spike: bool
    line_id: str
    line_label: str


class ScheduleResponse(BaseModel):
    schedule_id: str
    facility_id: str
    production_line: str
    line_id: str
    start_time: datetime
    duration_minutes: int
    devices: List[DeviceQuantity]
    probability_series: List[ProbabilityPoint]
    max_probability: float
    avg_probability: float
    predicted_spike: bool
    weather_snapshot: WeatherSnapshot
    maintenance_window: bool
    testing_or_calibration: bool
    unexpected_event: bool


class LineOption(BaseModel):
    id: str
    label: str


class DeviceOption(BaseModel):
    product_type: str
    display_name: str
    description: str
    sterilization_required: bool


class FacilityOption(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    timezone: str


class ConfigResponse(BaseModel):
    lines: List[LineOption]
    devices: List[DeviceOption]
    facilities: List[FacilityOption]
    weather_provider: str


class HeatmapPoint(BaseModel):
    timestamp: datetime
    line_id: str
    line_label: str
    probability: float
    spike: bool


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def _facility_timezone(facility_id: str) -> ZoneInfo:
    tz_name = FACILITIES[facility_id]["timezone"]
    return ZoneInfo(tz_name)


def _ensure_template() -> Dict[str, Any]:
    return {col: BASELINE_TEMPLATE.get(col, 0.0) for col in FEATURE_COLUMNS}


async def _fetch_weather(
    latitude: float, longitude: float, start: datetime, end: datetime
) -> List[Dict[str, Any]]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": WEATHER_PARAMETERS,
        "timezone": "UTC",
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(WEATHER_ENDPOINT, params=params)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=502, detail=f"Weather provider error: {exc}") from exc

    payload = response.json()
    hourly = payload.get("hourly")
    if not hourly:
        raise HTTPException(status_code=502, detail="Incomplete weather data received.")

    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    humidity = hourly.get("relative_humidity_2m", [])
    dew_points = hourly.get("dewpoint_2m", [])
    irradiance = hourly.get("direct_normal_irradiance", [])
    wind_speed = hourly.get("wind_speed_10m", [])

    series: List[Dict[str, Any]] = []
    for idx, timestamp_str in enumerate(times):
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        entry = {
            "timestamp": timestamp.replace(tzinfo=timezone.utc),
            "temperature_2m": float(temps[idx]) if idx < len(temps) and temps[idx] is not None else None,
            "relative_humidity_2m": float(humidity[idx])
            if idx < len(humidity) and humidity[idx] is not None
            else None,
            "dewpoint_2m": float(dew_points[idx]) if idx < len(dew_points) and dew_points[idx] is not None else None,
            "direct_normal_irradiance": float(irradiance[idx])
            if idx < len(irradiance) and irradiance[idx] is not None
            else 0.0,
            "wind_speed_10m": float(wind_speed[idx])
            if idx < len(wind_speed) and wind_speed[idx] is not None
            else 0.0,
        }
        series.append(entry)

    if not series:
        raise HTTPException(status_code=502, detail="Weather series empty for requested window.")
    return series


def _find_weather_point(series: List[Dict[str, Any]], target: datetime) -> Dict[str, Any]:
    target_utc = target.astimezone(timezone.utc)
    closest = min(series, key=lambda item: abs(item["timestamp"] - target_utc))
    return closest


def _compute_shift_id(hour: int) -> int:
    if 0 <= hour < 8:
        return 1
    if 8 <= hour < 16:
        return 2
    return 3


def _aggregate_device_demands(devices: List[DeviceQuantity]) -> Dict[str, Any]:
    total_quantity = sum(item.quantity for item in devices)
    sterilization_required = any(
        item.sterilization_override if item.sterilization_override is not None else DEVICE_PROFILES[item.product_type]["sterilization_required"]
        for item in devices
    )
    hvac_load = 0.0
    compressed_air = 0.0
    occupancy = 0.0
    calibration_events = any(item.calibration_event for item in devices)

    for item in devices:
        profile = DEVICE_PROFILES[item.product_type]
        quantity = item.quantity
        hvac_load += quantity * profile["hvac_factor"]
        compressed_air += quantity * profile["compressed_air_factor"]
        occupancy += quantity * profile["occupancy_per_unit"]

    return {
        "total_quantity": total_quantity,
        "sterilization_required": sterilization_required,
        "hvac_load": hvac_load,
        "compressed_air": compressed_air,
        "occupancy": occupancy,
        "calibration_events": calibration_events,
    }


def _build_feature_row(
    schedule: ScheduleRequest,
    slot_time_local: datetime,
    weather_current: Dict[str, Any],
    weather_next: Dict[str, Any],
    device_demand: Dict[str, Any],
    facility_id: str,
) -> Dict[str, Any]:
    feature = _ensure_template()
    line_id = LINE_LABEL_TO_ID[schedule.production_line]

    feature["facility_id"] = facility_id
    feature["line_id"] = line_id

    feature["hour_of_day"] = slot_time_local.hour
    feature["day_of_week"] = slot_time_local.isoweekday()
    feature["shift_id"] = _compute_shift_id(slot_time_local.hour)

    feature["maintenance_flag"] = int(schedule.maintenance_window)
    feature["post_maintenance_startup"] = int(schedule.testing_or_calibration or device_demand["calibration_events"])

    occupancy_base = BASELINE_TEMPLATE.get("cleanroom_occupancy_count", 12)
    projected_occupancy = min(25, max(0, occupancy_base + device_demand["occupancy"]))
    feature["cleanroom_occupancy_count"] = projected_occupancy

    cleanroom_temp_setpoint = BASELINE_TEMPLATE.get("cleanroom_temp_setpoint_C", 22.0)
    cleanroom_humidity_setpoint = BASELINE_TEMPLATE.get("cleanroom_humidity_setpoint_pct", 45.0)

    temp_increase = min(2.0, device_demand["hvac_load"] * 0.05)
    humidity_increase = min(5.0, device_demand["hvac_load"] * 0.08)
    if device_demand["sterilization_required"]:
        temp_increase += 0.4
        humidity_increase += 1.5

    feature["cleanroom_temp_C"] = cleanroom_temp_setpoint + temp_increase
    feature["cleanroom_humidity_pct"] = cleanroom_humidity_setpoint + humidity_increase
    feature["temp_diff_C"] = feature["cleanroom_temp_C"] - cleanroom_temp_setpoint
    feature["humidity_diff_pct"] = feature["cleanroom_humidity_pct"] - cleanroom_humidity_setpoint

    hvac_base = BASELINE_TEMPLATE.get("hvac_fan_speed_pct", 70.0)
    hvac_delta = min(20.0, device_demand["hvac_load"] * 0.4)
    feature["hvac_fan_speed_pct"] = min(100.0, hvac_base + hvac_delta)

    chiller_base = BASELINE_TEMPLATE.get("chiller_load_pct", 60.0)
    chiller_delta = min(25.0, device_demand["hvac_load"] * 0.3)
    feature["chiller_load_pct"] = min(100.0, chiller_base + chiller_delta)

    compressor_base = BASELINE_TEMPLATE.get("compressor_count_running", 1)
    compressor_delta = 0
    if device_demand["compressed_air"] > 0:
        compressor_delta = min(2, int(round(device_demand["compressed_air"] / 25.0)))
    if schedule.unexpected_event:
        compressor_delta += 1
    feature["compressor_count_running"] = min(4, compressor_base + compressor_delta)

    vacuum_base = BASELINE_TEMPLATE.get("vacuum_pump_power_kW", 6.0)
    feature["vacuum_pump_power_kW"] = vacuum_base + device_demand["compressed_air"] * 0.05

    feature["autoclave_state"] = "Heat" if device_demand["sterilization_required"] else "Off"
    feature["autoclave_cycle_active"] = int(device_demand["sterilization_required"])

    feature["room_pressure_Pa"] = BASELINE_TEMPLATE.get("room_pressure_Pa", 15)
    if schedule.unexpected_event:
        feature["room_pressure_Pa"] = feature["room_pressure_Pa"] + 1

    weather_temp = weather_current.get("temperature_2m")
    weather_humidity = weather_current.get("relative_humidity_2m")
    weather_dewpoint = weather_current.get("dewpoint_2m")
    weather_irradiance = weather_current.get("direct_normal_irradiance", 0.0) or 0.0
    weather_wind = weather_current.get("wind_speed_10m", 0.0) or 0.0

    feature["outdoor_temp_C"] = weather_temp if weather_temp is not None else feature.get("outdoor_temp_C", 18.0)
    feature["outdoor_humidity_pct"] = weather_humidity if weather_humidity is not None else feature.get("outdoor_humidity_pct", 45.0)
    feature["dew_point_C"] = weather_dewpoint if weather_dewpoint is not None else feature.get("dew_point_C", 10.0)
    feature["solar_irradiance_Wm2"] = max(0.0, weather_irradiance)
    feature["wind_speed_mps"] = weather_wind

    feature["forecast_temp_next1h"] = (
        weather_next.get("temperature_2m") if weather_next.get("temperature_2m") is not None else feature["outdoor_temp_C"]
    )
    feature["forecast_humidity_next1h"] = (
        weather_next.get("relative_humidity_2m")
        if weather_next.get("relative_humidity_2m") is not None
        else feature["outdoor_humidity_pct"]
    )

    baseline_outdoor_temp = BASELINE_TEMPLATE.get("outdoor_temp_C", feature["outdoor_temp_C"])
    baseline_outdoor_humidity = BASELINE_TEMPLATE.get("outdoor_humidity_pct", feature["outdoor_humidity_pct"])

    feature["outdoor_temp_delta"] = feature["outdoor_temp_C"] - baseline_outdoor_temp
    feature["humidity_delta"] = feature["outdoor_humidity_pct"] - baseline_outdoor_humidity
    feature["occupancy_delta"] = feature["cleanroom_occupancy_count"] - occupancy_base

    feature["air_pressure_bar"] = BASELINE_TEMPLATE.get("air_pressure_bar", 6.2) + device_demand["compressed_air"] * 0.002
    feature["dry_air_dew_point_C"] = feature["dew_point_C"] - 1.5

    feature["batch_status"] = "Running"
    feature["product_type"] = schedule.devices[0].product_type

    return {col: feature.get(col, 0.0) for col in FEATURE_COLUMNS}


def _load_schedules() -> List[Dict[str, Any]]:
    if not SCHEDULES_PATH.exists():
        return []
    try:
        with SCHEDULES_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError:
        return []


def _save_schedules(schedules: List[Dict[str, Any]]) -> None:
    with SCHEDULES_PATH.open("w", encoding="utf-8") as handle:
        json.dump(schedules, handle, indent=2)


def _build_heatmap(points: List[Dict[str, Any]]) -> List[HeatmapPoint]:
    buckets: Dict[tuple, List[float]] = {}
    for record in points:
        line_id = record["line_id"]
        line_label = LINE_ID_TO_LABEL.get(line_id, line_id)
        for point in record["probability_series"]:
            timestamp = datetime.fromisoformat(point["timestamp"])
            key = (timestamp, line_id)
            buckets.setdefault(key, []).append(point["probability"])

    heatmap: List[HeatmapPoint] = []
    for (timestamp, line_id), probs in buckets.items():
        avg_prob = sum(probs) / len(probs)
        heatmap.append(
            HeatmapPoint(
                timestamp=timestamp,
                line_id=line_id,
                line_label=LINE_ID_TO_LABEL.get(line_id, line_id),
                probability=avg_prob,
                spike=avg_prob >= 0.6,
            )
        )
    heatmap.sort(key=lambda item: item.timestamp)
    return heatmap


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
@app.get("/config", response_model=ConfigResponse)
async def get_configuration() -> ConfigResponse:
    lines = [LineOption(**item) for item in LINE_OPTIONS]
    devices = [
        DeviceOption(
            product_type=key,
            display_name=value["display_name"],
            description=value["description"],
            sterilization_required=value["sterilization_required"],
        )
        for key, value in DEVICE_PROFILES.items()
    ]
    facilities = [
        FacilityOption(
            id=item["id"],
            name=item["name"],
            latitude=item["latitude"],
            longitude=item["longitude"],
            timezone=item["timezone"],
        )
        for item in FACILITIES.values()
    ]
    return ConfigResponse(
        lines=lines,
        devices=devices,
        facilities=facilities,
        weather_provider="open-meteo.com",
    )


@app.get("/schedules", response_model=List[ScheduleResponse])
async def list_schedules() -> List[ScheduleResponse]:
    records = _load_schedules()
    return [ScheduleResponse(**record) for record in records]


@app.get("/predictions/heatmap", response_model=List[HeatmapPoint])
async def heatmap_view() -> List[HeatmapPoint]:
    records = _load_schedules()
    heatmap = _build_heatmap(records)
    return heatmap


@app.post("/schedule", response_model=ScheduleResponse)
async def create_schedule(payload: ScheduleRequest) -> ScheduleResponse:
    facility = FACILITIES[payload.facility_id]
    facility_tz = _facility_timezone(payload.facility_id)

    start_local = payload.start_time
    if start_local.tzinfo is None:
        start_local = start_local.replace(tzinfo=facility_tz)
    else:
        start_local = payload.start_time.astimezone(facility_tz)

    horizon_hours = max(6, int((payload.duration_minutes + 180) // 60) + 2)
    end_local = start_local + timedelta(hours=horizon_hours)

    weather_series = await _fetch_weather(
        latitude=facility["latitude"],
        longitude=facility["longitude"],
        start=start_local.astimezone(timezone.utc),
        end=end_local.astimezone(timezone.utc),
    )

    device_demand = _aggregate_device_demands(payload.devices)

    series_points: List[ProbabilityPoint] = []
    slot_count = int(((end_local - start_local).total_seconds() // 60) / SERIES_INTERVAL_MINUTES) + 1

    for slot_index in range(slot_count):
        slot_time = start_local + timedelta(minutes=slot_index * SERIES_INTERVAL_MINUTES)
        weather_current = _find_weather_point(weather_series, slot_time)
        next_time = slot_time + timedelta(hours=1)
        weather_next = _find_weather_point(weather_series, next_time)

        feature_row = _build_feature_row(
            schedule=payload,
            slot_time_local=slot_time,
            weather_current=weather_current,
            weather_next=weather_next,
            device_demand=device_demand,
            facility_id=payload.facility_id,
        )

        df = pd.DataFrame([feature_row])
        probability = float(MODEL_PIPELINE.predict_proba(df)[0][1])
        spike = bool(probability >= 0.6)

        series_points.append(
            ProbabilityPoint(
                timestamp=slot_time,
                probability=probability,
                spike=spike,
                line_id=LINE_LABEL_TO_ID[payload.production_line],
                line_label=payload.production_line,
            )
        )

    weather_at_start = _find_weather_point(weather_series, start_local)
    weather_snapshot = WeatherSnapshot(
        temperature_c=weather_at_start.get("temperature_2m", BASELINE_TEMPLATE.get("outdoor_temp_C", 20.0)),
        humidity_pct=weather_at_start.get("relative_humidity_2m", BASELINE_TEMPLATE.get("outdoor_humidity_pct", 45.0)),
        dew_point_c=weather_at_start.get("dewpoint_2m", BASELINE_TEMPLATE.get("dew_point_C", 10.0)),
        solar_irradiance_wm2=max(0.0, weather_at_start.get("direct_normal_irradiance", 0.0) or 0.0),
        wind_speed_mps=weather_at_start.get("wind_speed_10m", BASELINE_TEMPLATE.get("wind_speed_mps", 3.0)),
    )

    probabilities = [point.probability for point in series_points]
    max_probability = max(probabilities)
    avg_probability = sum(probabilities) / len(probabilities)
    predicted_spike = any(point.spike for point in series_points)

    schedule_record = ScheduleResponse(
        schedule_id=str(uuid4()),
        facility_id=payload.facility_id,
        production_line=payload.production_line,
        line_id=LINE_LABEL_TO_ID[payload.production_line],
        start_time=start_local,
        duration_minutes=payload.duration_minutes,
        devices=payload.devices,
        probability_series=series_points,
        max_probability=max_probability,
        avg_probability=avg_probability,
        predicted_spike=predicted_spike,
        weather_snapshot=weather_snapshot,
        maintenance_window=payload.maintenance_window,
        testing_or_calibration=payload.testing_or_calibration,
        unexpected_event=payload.unexpected_event,
    )

    stored_records = _load_schedules()
    stored_records.append(json.loads(schedule_record.json()))
    _save_schedules(stored_records)

    return schedule_record


@app.get("/health")
async def healthcheck() -> Dict[str, Any]:
    return {"status": "ok", "model_ready": True, "schedules_cached": len(_load_schedules())}
