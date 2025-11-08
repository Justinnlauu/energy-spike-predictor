import React, { useMemo } from "react";
import dayjs from "dayjs";

const probabilityClass = (value) => {
  if (value >= 0.75) {
    return "pill danger";
  }
  if (value >= 0.6) {
    return "pill info";
  }
  return "pill success";
};

function ScheduleTable({ schedules, selectedId, onSelect }) {
  const rows = useMemo(() => {
    if (!schedules?.length) {
      return [];
    }
    return [...schedules].sort(
      (a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime()
    );
  }, [schedules]);

  if (!rows.length) {
    return (
      <div>
        <h2>Scheduled Runs</h2>
        <p style={{ color: "#475569" }}>
          Saved schedules will appear here. Select one to inspect its probability curve
          and weather-adjusted spike outlook.
        </p>
      </div>
    );
  }

  return (
    <div className="table-list">
      <h2>Scheduled Runs</h2>
      <table>
        <thead>
          <tr>
            <th>Start</th>
            <th>Line</th>
            <th>Max Probability</th>
            <th>Average</th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((schedule) => {
            const isSelected = schedule.schedule_id === selectedId;
            return (
              <tr
                key={schedule.schedule_id}
                className={isSelected ? "selected" : ""}
                onClick={() => onSelect(schedule.schedule_id)}
              >
                <td>{dayjs(schedule.start_time).format("MMM D · HH:mm")}</td>
                <td>{schedule.production_line}</td>
                <td>
                  <span className={probabilityClass(schedule.max_probability)}>
                    {(schedule.max_probability * 100).toFixed(1)}%
                  </span>
                </td>
                <td>{(schedule.avg_probability * 100).toFixed(1)}%</td>
                <td className="flag-cell">
                  {schedule.maintenance_window && <span className="badge info">Maintenance</span>}
                  {schedule.testing_or_calibration && (
                    <span className="badge info">Calibration</span>
                  )}
                  {schedule.unexpected_event && <span className="badge danger">Unexpected</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default ScheduleTable;
