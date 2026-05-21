import { useState } from "react";
import { Luggage } from "lucide-react";

export default function PackingChecklist({ items }) {
  const [checked, setChecked] = useState({});

  if (!items || items.length === 0) return null;

  const toggle = (i) => setChecked((prev) => ({ ...prev, [i]: !prev[i] }));

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <Luggage size={16} style={{ color: "var(--color-primary)" }} />
        <h3 className="font-semibold text-sm">Packing List</h3>
      </div>
      <div className="space-y-1.5">
        {items.map((item, i) => (
          <label key={i} className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={!!checked[i]}
              onChange={() => toggle(i)}
              className="rounded border-gray-300 text-[var(--color-primary)] focus:ring-[var(--color-primary-light)]"
            />
            <span className={checked[i] ? "line-through text-gray-400" : ""}>{item}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
