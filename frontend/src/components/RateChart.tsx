/**
 * Recharts line chart for EUR→USD movement over time.
 */
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DayRate } from "../types";

interface RateChartProps {
  days: DayRate[];
}

/** Custom tooltip showing precise rate values on hover. */
function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-panel rounded-2xl px-4 py-3 text-sm shadow-2xl">
      <p className="text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 font-semibold text-[var(--text-primary)]">
        {Number(payload[0].value).toFixed(4)} USD
      </p>
    </div>
  );
}

/** Area chart visualizing the EUR→USD trend for the selected period. */
export function RateChart({ days }: RateChartProps) {
  return (
    <div className="h-[22rem]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={days} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="rateGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.45} />
              <stop offset="100%" stopColor="#6366f1" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={56}
            tickFormatter={(value) => Number(value).toFixed(3)}
          />
          <Tooltip content={<ChartTooltip />} />
          <Area
            type="monotone"
            dataKey="rate"
            stroke="#38bdf8"
            strokeWidth={3}
            fill="url(#rateGradient)"
            dot={{ r: 4, fill: "#38bdf8", strokeWidth: 0 }}
            activeDot={{ r: 6, fill: "#a855f7" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
