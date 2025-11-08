import React from "react";
import dayjs from "dayjs";

const formatPercentage = (value) => `${(value * 100).toFixed(1)}%`;

function ScheduleSummary({ schedule }) {
  if (!schedule) {
    return (
      <div>
        <h2>Schedule Snapshot</h2>
        <p style={{ color: "#475569" }}>
          Create a schedule to populate the prediction summary. Weather insights,
          predicted spike probability, and operational indicators will appear here as
          soon as a run is saved.
        </p>
      </div>
    );
  }

  const startTime = dayjs(schedule.start_time);
  const endTime = startTime.add(schedule.duration_minutes, "minute");

  return (
    <div className="schedule-summary">
      <div className="summary-header">
        <div>
          <h2>Schedule Snapshot</h2>
          <span className={`pill ${schedule.predicted_spike ? "danger" : "success"}`}>
            {schedule.predicted_spike ? "High Spike Risk" : "Stable Load"}
          </span>
        </div>
        <div className="badge muted">Line: {schedule.production_line}</div>
      </div>

      <div className="grid two summary-grid">
        <div className="summary-card">
          <h4>Timing</h4>
          <p>
            {startTime.format("MMM D, YYYY · HH:mm")} → {endTime.format("HH:mm")}
          </p>
          <p className="muted">
            Duration: <strong>{schedule.duration_minutes}</strong> minutes
          </p>
          <p className="muted">
            Facility: <strong>{schedule.facility_id}</strong>
          </p>
        </div>

        <div className="summary-card">
          <h4>Probability</h4>
          <p>
            Max spike probability: <strong>{formatPercentage(schedule.max_probability)}</strong>
          </p>
          <p>
            Average probability:{" "}
            <strong>{formatPercentage(schedule.avg_probability)}</strong>
          </p>
          <p className="muted">
            Data points: {schedule.probability_series.length.toLocaleString()}
          </p>
        </div>
      </div>

      <div className="grid two summary-grid">
        <div className="summary-card">
          <h4>Device Mix</h4>
          <ul>
            {schedule.devices.map((device, index) => (
              <li key={index}>
                <strong>{device.product_type.replace(/_/g, " ")}</strong> ·{" "}
                {device.quantity.toLocaleString()} units{" "}
                {device.calibration_event && (
                  <span className="badge info">Calibration</span>
                )}
              </li>
            ))}
          </ul>
        </div>

        <div className="summary-card weather">
          <h4>Weather at Start</h4>
          <div className="weather-grid">
            <div>
              <span className="muted">Temperature</span>
              <strong>{schedule.weather_snapshot.temperature_c.toFixed(1)} °C</strong>
            </div>
            <div>
              <span className="muted">Humidity</span>
              <strong>{schedule.weather_snapshot.humidity_pct.toFixed(1)} %</strong>
            </div>
            <div>
              <span className="muted">Dew Point</span>
              <strong>{schedule.weather_snapshot.dew_point_c.toFixed(1)} °C</strong>
            </div>
            <div>
              <span className="muted">Solar</span>
              <strong>{schedule.weather_snapshot.solar_irradiance_wm2.toFixed(0)} W/m²</strong>
            </div>
            <div>
              <span className="muted">Wind</span>
              <strong>{schedule.weather_snapshot.wind_speed_mps.toFixed(1)} m/s</strong>
            </div>
          </div>
        </div>
      </div>

      <div className="summary-flags">
        <h4>Operational Signals</h4>
        <div className="flag-group">
          <span className={`pill ${schedule.maintenance_window ? "info" : "muted"}`}>
            Maintenance {schedule.maintenance_window ? "Planned" : "Not planned"}
          </span>
          <span className={`pill ${schedule.testing_or_calibration ? "info" : "muted"}`}>
            Testing & Calibration{" "}
            {schedule.testing_or_calibration ? "Scheduled" : "Not scheduled"}
          </span>
          <span className={`pill ${schedule.unexpected_event ? "danger" : "muted"}`}>
            Unexpected Events {schedule.unexpected_event ? "Flagged" : "None"}
          </span>
        </div>
      </div>
    </div>
  );
}

export default ScheduleSummary;
