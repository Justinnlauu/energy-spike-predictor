import React, { useMemo } from "react";
import dayjs from "dayjs";
import {
  Area,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const formatTimestampLabel = (value) => dayjs(value).format("MMM D HH:mm");

const tooltipFormatter = (value) => `${(value * 100).toFixed(2)}%`;

function ProbabilityChart({ series }) {
  const data = useMemo(() => {
    if (!series?.length) {
      return [];
    }
    return series.map((point) => ({
      timestamp: point.timestamp,
      label: formatTimestampLabel(point.timestamp),
      probability: point.probability,
      spike: point.spike,
    }));
  }, [series]);

  if (!data.length) {
    return (
      <div style={{ color: "#475569" }}>
        No probability data yet. Submit a schedule to generate a risk timeline.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={340}>
      <LineChart data={data} margin={{ top: 12, right: 24, bottom: 12, left: 8 }}>
        <CartesianGrid stroke="rgba(148, 163, 184, 0.25)" strokeDasharray="4 4" />
        <XAxis
          dataKey="label"
          tickFormatter={(value) => dayjs(value, "MMM D HH:mm").format("HH:mm")}
          minTickGap={32}
        />
        <YAxis
          domain={[0, 1]}
          tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
          width={56}
        />
        <Tooltip
          formatter={tooltipFormatter}
          labelFormatter={(label) => label}
          contentStyle={{ borderRadius: 12, border: "1px solid #cbd5f5" }}
        />
        <ReferenceLine
          y={0.6}
          stroke="#f97316"
          strokeDasharray="6 6"
          label={{ value: "Spike Threshold (60%)", position: "insideTopRight", fill: "#ea580c" }}
        />
        <Area
          type="monotone"
          dataKey="probability"
          stroke="rgba(37, 99, 235, 0.4)"
          fill="rgba(59, 130, 246, 0.25)"
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="probability"
          stroke="#2563eb"
          strokeWidth={2.4}
          dot={{ stroke: "#1d4ed8", strokeWidth: 1, r: 3 }}
          activeDot={{ r: 5, fill: "#1d4ed8" }}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export default ProbabilityChart;
