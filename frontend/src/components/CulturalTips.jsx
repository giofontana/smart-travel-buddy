import { useState } from "react";
import { Globe, ChevronDown, ChevronRight } from "lucide-react";

export default function CulturalTips({ tips }) {
  const [expanded, setExpanded] = useState(false);

  if (!tips || tips.length === 0) return null;

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4">
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <Globe size={16} style={{ color: "var(--color-primary)" }} />
          <h3 className="font-semibold text-sm">Cultural Tips</h3>
        </div>
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </div>
      {expanded && (
        <ul className="mt-3 space-y-1.5">
          {tips.map((tip, i) => (
            <li key={i} className="text-sm flex gap-2">
              <span className="text-amber-500 mt-0.5">&#8226;</span>
              <span>{tip}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
