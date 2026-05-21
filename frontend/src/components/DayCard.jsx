import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import WeatherBadge from "./WeatherBadge";

const TIME_COLORS = {
  morning: "bg-amber-100 text-amber-800",
  afternoon: "bg-sky-100 text-sky-800",
  evening: "bg-indigo-100 text-indigo-800",
};

export default function DayCard({ day, dayNumber }) {
  const [expanded, setExpanded] = useState(true);

  const date = new Date(day.date + "T00:00:00");
  const formattedDate = date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });

  return (
    <div className="animate-fade-in bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl overflow-hidden">
      {/* Day header */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className="text-xs font-bold text-white bg-[var(--color-primary)] rounded-full w-7 h-7 flex items-center justify-center">
            {dayNumber}
          </div>
          <div>
            <div className="font-semibold text-sm">{formattedDate}</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <WeatherBadge weather={day.weather} />
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </div>

      {/* Activities */}
      {expanded && (
        <div className="px-4 pb-3 space-y-2">
          {day.activities?.map((activity, i) => (
            <div key={i} className="flex gap-3 py-2 border-t border-[var(--color-border)] first:border-t-0">
              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full h-fit mt-0.5 ${TIME_COLORS[activity.time] || TIME_COLORS.morning}`}>
                {activity.time}
              </span>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm">{activity.name}</div>
                <div className="text-xs mt-0.5" style={{ color: "var(--color-text-muted)" }}>
                  {activity.description}
                </div>
                {activity.tip && (
                  <div className="text-xs mt-1 italic text-amber-700">
                    Tip: {activity.tip}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
