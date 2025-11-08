import React, { useEffect, useMemo, useState } from "react";
import dayjs from "dayjs";

const formatLocalDateTime = (value) => dayjs(value).format("YYYY-MM-DDTHH:mm");

const buildInitialDevice = (productType) => ({
  product_type: productType ?? "",
  quantity: 100,
  calibration_event: false,
});

const DEFAULT_DURATION = 120;

function ScheduleForm({ config, onSubmit }) {
  if (!config) {
    return <p style={{ color: "#475569" }}>Loading configuration…</p>;
  }

  const defaultFacility = config?.facilities?.[0]?.id ?? "";
  const defaultLine = config?.lines?.[0]?.label ?? "";
  const defaultDeviceType = config?.devices?.[0]?.product_type ?? "";

  const [facilityId, setFacilityId] = useState(defaultFacility);
  const [productionLine, setProductionLine] = useState(defaultLine);
  const [startTime, setStartTime] = useState(
    formatLocalDateTime(dayjs().add(1, "hour").startOf("hour"))
  );
  const [durationMinutes, setDurationMinutes] = useState(DEFAULT_DURATION);
  const [devices, setDevices] = useState([buildInitialDevice(defaultDeviceType)]);
  const [maintenanceWindow, setMaintenanceWindow] = useState(false);
  const [testingCalibration, setTestingCalibration] = useState(false);
  const [unexpectedEvent, setUnexpectedEvent] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    if (!config) {
      return;
    }
    setFacilityId(defaultFacility);
    setProductionLine(defaultLine);
    setDevices([buildInitialDevice(defaultDeviceType)]);
  }, [config, defaultFacility, defaultLine, defaultDeviceType]);

  const facilityOptions = config?.facilities ?? [];
  const lineOptions = config?.lines ?? [];
  const deviceOptions = config?.devices ?? [];

  const totalQuantity = useMemo(
    () => devices.reduce((sum, device) => sum + Number(device.quantity || 0), 0),
    [devices]
  );

  const handleDeviceFieldChange = (index, field, value) => {
    setDevices((current) =>
      current.map((device, deviceIndex) =>
        deviceIndex === index
          ? {
              ...device,
              [field]: field === "quantity" ? Number(value) || 0 : value,
            }
          : device
      )
    );
  };

  const handleToggleCalibration = (index) => {
    setDevices((current) =>
      current.map((device, deviceIndex) =>
        deviceIndex === index
          ? { ...device, calibration_event: !device.calibration_event }
          : device
      )
    );
  };

  const handleAddDevice = () => {
    setDevices((current) => [...current, buildInitialDevice(defaultDeviceType)]);
  };

  const handleRemoveDevice = (index) => {
    if (devices.length === 1) {
      return;
    }
    setDevices((current) => current.filter((_, i) => i !== index));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSuccessMessage("");

    if (!facilityId || !productionLine) {
      setError("Facility and production line are required.");
      return;
    }

    if (devices.some((device) => !device.product_type || Number(device.quantity) <= 0)) {
      setError("Each device entry must include a product type and quantity greater than zero.");
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        facility_id: facilityId,
        production_line: productionLine,
        start_time: dayjs(startTime).toDate().toISOString(),
        duration_minutes: Number(durationMinutes),
        devices: devices.map((device) => ({
          product_type: device.product_type,
          quantity: Number(device.quantity),
          calibration_event: Boolean(device.calibration_event),
        })),
        maintenance_window: maintenanceWindow,
        testing_or_calibration: testingCalibration,
        unexpected_event: unexpectedEvent,
      };

      await onSubmit(payload);
      setSuccessMessage("Schedule saved and predictions updated.");
    } catch (err) {
      setError(err?.message ?? "Failed to create schedule.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="schedule-form">
      <h2>Schedule Production Run</h2>
      <p style={{ marginTop: "0.25rem", color: "#475569" }}>
        Configure the next manufacturing batch, including line assignment, device mix,
        and operational context. The predictor will use this detail plus weather
        inputs to score spike risk.
      </p>

      <div className="form-section">
        <label htmlFor="facility">Facility</label>
        <select
          id="facility"
          value={facilityId}
          onChange={(event) => setFacilityId(event.target.value)}
        >
          {facilityOptions.map((facility) => (
            <option key={facility.id} value={facility.id}>
              {facility.name}
            </option>
          ))}
        </select>
      </div>

      <div className="form-section">
        <label htmlFor="line">Production Line</label>
        <select
          id="line"
          value={productionLine}
          onChange={(event) => setProductionLine(event.target.value)}
        >
          {lineOptions.map((line) => (
            <option key={line.id} value={line.label}>
              {line.label}
            </option>
          ))}
        </select>
      </div>

      <div className="grid two">
        <div className="form-section">
          <label htmlFor="start-time">Start Time</label>
          <input
            id="start-time"
            type="datetime-local"
            value={startTime}
            onChange={(event) => setStartTime(event.target.value)}
          />
        </div>
        <div className="form-section">
          <label htmlFor="duration">Duration (minutes)</label>
          <input
            id="duration"
            type="number"
            min={30}
            max={1440}
            value={durationMinutes}
            onChange={(event) => setDurationMinutes(Number(event.target.value))}
          />
        </div>
      </div>

      <div className="form-section device-section">
        <div className="device-header">
          <h3>Devices in Batch</h3>
          <button type="button" onClick={handleAddDevice} className="text-button">
            + Add device
          </button>
        </div>
        <div className="device-list">
          {devices.map((device, index) => (
            <div key={index} className="device-row">
              <div className="device-field">
                <label>Product</label>
                <select
                  value={device.product_type}
                  onChange={(event) =>
                    handleDeviceFieldChange(index, "product_type", event.target.value)
                  }
                >
                  {deviceOptions.map((option) => (
                    <option key={option.product_type} value={option.product_type}>
                      {option.display_name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="device-field">
                <label>Quantity</label>
                <input
                  type="number"
                  min={1}
                  value={device.quantity}
                  onChange={(event) =>
                    handleDeviceFieldChange(index, "quantity", event.target.value)
                  }
                />
              </div>
              <div className="device-field device-toggle">
                <label>Calibration</label>
                <button
                  type="button"
                  className={`pill ${device.calibration_event ? "info" : "muted"}`}
                  onClick={() => handleToggleCalibration(index)}
                >
                  {device.calibration_event ? "Included" : "Not included"}
                </button>
              </div>
              {devices.length > 1 && (
                <button
                  type="button"
                  className="remove-button"
                  onClick={() => handleRemoveDevice(index)}
                >
                  Remove
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="form-section flags">
        <h3>Operational Context</h3>
        <div className="flag-buttons">
          <button
            type="button"
            className={`pill ${maintenanceWindow ? "info" : "muted"}`}
            onClick={() => setMaintenanceWindow((value) => !value)}
          >
            Maintenance Window {maintenanceWindow ? "On" : "Off"}
          </button>
          <button
            type="button"
            className={`pill ${testingCalibration ? "info" : "muted"}`}
            onClick={() => setTestingCalibration((value) => !value)}
          >
            Testing & Calibration {testingCalibration ? "On" : "Off"}
          </button>
          <button
            type="button"
            className={`pill ${unexpectedEvent ? "danger" : "muted"}`}
            onClick={() => setUnexpectedEvent((value) => !value)}
          >
            Unexpected Demand {unexpectedEvent ? "Flagged" : "None"}
          </button>
        </div>
      </div>

      <div className="form-footer">
        <div className="batch-stats">
          <span>Total quantity</span>
          <strong>{totalQuantity.toLocaleString()}</strong>
        </div>
        <button type="submit" disabled={submitting}>
          {submitting ? "Submitting..." : "Save Schedule & Predict"}
        </button>
      </div>

      {error && (
        <div className="alert danger" role="alert">
          {error}
        </div>
      )}
      {successMessage && (
        <div className="alert success" role="status">
          {successMessage}
        </div>
      )}
    </form>
  );
}

export default ScheduleForm;
