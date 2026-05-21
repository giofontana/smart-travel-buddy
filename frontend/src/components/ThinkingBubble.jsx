import { useState } from "react";
import { ChevronDown, ChevronRight, Brain } from "lucide-react";

export default function ThinkingBubble({ content }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="animate-fade-in flex justify-start mb-2">
      <div
        className="max-w-[80%] rounded-lg px-3 py-2 text-sm cursor-pointer select-none"
        style={{ backgroundColor: "var(--color-thinking)", color: "var(--color-text-muted)" }}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-1.5 font-medium">
          <Brain size={14} />
          <span>Thinking</span>
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
        {expanded && (
          <div className="mt-2 italic whitespace-pre-wrap text-xs leading-relaxed">
            {content}
          </div>
        )}
      </div>
    </div>
  );
}
