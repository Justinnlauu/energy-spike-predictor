import React, { useMemo } from "react";
import dayjs from "dayjs";

const probabilityToColor = (probability) => {
  const hue = Math.max(0, Math.min(120, Math.round((1 - probability) * 120)));
  const saturation = 70;
  const lightness = 45 + probability * 10;
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
};

function HeatmapGrid({ data }) {
  const prepared = useMemo(() => {
    if (!data?.length) {
      return { lines: [], times: [], lookup: new Map() };
    }

    const lineOrder = Array.from(
      new Set(data.map((item) => item.line_label || item.line_id))
    );
    const times = Array.from(
      new Set(data.map((item) => dayjs(item.timestamp).format("MMM D HH:mm")))
    ).sort((a, b) => (dayjs(a, "MMM D HH:mm").isAfter(dayjs(b, "MMM D HH:mm")) ? 1 : -1));

    const lookup = new Map();
    data.forEach((item) => {
      const key = `${item.line_label || item.line_id}__${dayjs(item.timestamp).format(
        "MMM D HH:mm"
      )}`;
      lookup.set(key, item.probability);
    });

    return { lines: lineOrder, times, lookup };
  }, [data]);

  if (!prepared.times.length) {
    return (
      <div style={{ color: "#475569" }}>
        Heatmap will populate after schedules are created and predicted. Each cell shows
        the average spike probability for a line at a specific time block.
      </div>
    );
  }

  return (
    <div className="heatmap-grid">
      <table>
        <thead>
          <tr>
            <th>Line / Time</th>
            {prepared.times.map((time) => (
              <th key={time}>{time}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {prepared.lines.map((line) => (
            <tr key={line}>
              <td style={{ fontWeight: 600, backgroundColor: "rgba(15,23,42,0.07)" }}>
                {line}
              </td>
              {prepared.times.map((time) => {
                const key = `${line}__${time}`;
                const value = prepared.lookup.get(key);
                const textColor = value && value >= 0.6 ? "#1c1917" : "#0f172a";
                return (
                  <td
                    key={key}
                    style={{
                      backgroundColor: value !== undefined ? probabilityToColor(value) : "#e2e8f0",
                      color: value !== undefined ? textColor : "#64748b",
                      fontWeight: value !== undefined && value >= 0.6 ? 600 : 500,
                    }}
                  >
                    {value !== undefined ? `${(value * 100).toFixed(0)}%` : "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default HeatmapGrid;
