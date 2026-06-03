import { Activity } from "lucide-react";

export default function FlowToggle({ isOpen, onToggle }) {
  return (
    <button
      onClick={onToggle}
      title={isOpen ? "Hide flow diagram" : "Show flow diagram"}
      className="fixed z-[101] w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
      style={{
        bottom: isOpen ? "204px" : "20px",
        right: "20px",
        background: "rgba(12, 12, 30, 0.9)",
        border: "1px solid rgba(100, 100, 255, 0.25)",
        color: isOpen ? "#80cbc4" : "#666",
        boxShadow: "0 2px 12px rgba(0,0,0,0.3)",
      }}
    >
      <Activity size={18} />
    </button>
  );
}
