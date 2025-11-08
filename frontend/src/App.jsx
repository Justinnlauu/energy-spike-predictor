import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";

import ScheduleForm from "./components/ScheduleForm";
import ScheduleSummary from "./components/ScheduleSummary";
import ProbabilityChart from "./components/ProbabilityChart";
import HeatmapGrid from "./components/HeatmapGrid";
import ScheduleTable from "./components/ScheduleTable";

dayjs.extend(utc);
dayjs.extend(timezone);

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const extractErrorMessage = (error) => {
  if (error?.response?.data?.detail) {
    return Array.isArray(error.response.data.detail)
      ? error.response.data.detail.map((item) => item.msg || item).join(", ")
      : error.response.data.detail;
  }
  return error?.message || "Unexpected error occurred.";
};

function App() {
  const [config, setConfig] = useState(null);
  const [schedules, setSchedules] = useState([]);
  const [heatmapData, setHeatmapData] = useState([]);
  const [initializing, setInitializing] = useState(true);
  const [error, setError] = useState("");
  const [selectedScheduleId, setSelectedScheduleId] = useState(null);

  useEffect(() => {
    const fetchInitialData = async () => {
      setInitializing(true);
      setError("");
      try {
        const [configRes, schedulesRes, heatmapRes] = await Promise.all([
          axios.get(`${API_BASE_URL}/config`),
          axios.get(`${API_BASE_URL}/schedules`),
          axios.get(`${API_BASE_URL}/predictions/heatmap`),
        ]);

        setConfig(configRes.data);
        setSchedules(schedulesRes.data);
        setHeatmapData(heatmapRes.data);

        if (schedulesRes.data.length > 0) {
          const latestSchedule = [...schedulesRes.data].sort(
            (a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime()
          )[0];
          setSelectedScheduleId(latestSchedule.schedule_id);
        }
      } catch (err) {
        setError(extractErrorMessage(err));
      } finally {
        setInitializing(false);
      }
    };

    fetchInitialData();
  }, []);

  const selectedSchedule = useMemo(
    () => schedules.find((schedule) => schedule.schedule_id === selectedScheduleId) || null,
    [schedules, selectedScheduleId]
  );

  const handleScheduleSubmit = async (payload) => {
    setError("");
    try {
      const response = await axios.post(`${API_BASE_URL}/schedule`, payload);
      const newSchedule = response.data;
      setSchedules((current) => [...current, newSchedule]);
      setSelectedScheduleId(newSchedule.schedule_id);

      const heatmapResponse = await axios.get(`${API_BASE_URL}/predictions/heatmap`);
      setHeatmapData(heatmapResponse.data);

      return newSchedule;
    } catch (err) {
      const message = extractErrorMessage(err);
      setError(message);
      throw new Error(message);
    }
  };

  if (initializing) {
    return (
      <div className="app-shell">
        <div className="card">
          <h2>Loading environment</h2>
          <p>Fetching configuration, historical schedules, and current heatmap data…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header style={{ marginBottom: "2rem" }}>
        <span className="badge muted">Version {__APP_VERSION__}</span>
        <h1 style={{ marginBottom: "0.4rem", marginTop: "0.6rem" }}>
          Energy Spike Prediction Control Center
        </h1>
        <p style={{ maxWidth: "640px", color: "#475569" }}>
          Coordinate production, track environmental context, and surface high-risk energy
          windows for sterilization, HVAC, compressed air, and manufacturing events in one
          predictive dashboard.
        </p>
        {error && (
          <div className="alert danger" role="alert" style={{ marginTop: "1rem" }}>
            {error}
          </div>
        )}
      </header>

      <div className="grid two">
        <div className="card">
          <ScheduleForm config={config} onSubmit={handleScheduleSubmit} />
        </div>
        <div className="card">
          <ScheduleSummary schedule={selectedSchedule} />
        </div>
      </div>

      <h3 className="section-title">Probability Timeline</h3>
      <div className="card">
        <ProbabilityChart series={selectedSchedule?.probability_series ?? []} />
      </div>

      <h3 className="section-title">Demand Heatmap</h3>
      <div className="card">
        <HeatmapGrid data={heatmapData} />
      </div>

      <h3 className="section-title">All Schedules</h3>
      <div className="card">
        <ScheduleTable
          schedules={schedules}
          selectedId={selectedScheduleId}
          onSelect={setSelectedScheduleId}
        />
      </div>
    </div>
  );
}

export default App;
