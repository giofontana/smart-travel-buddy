import { Cloud, ArrowLeftRight, BookOpen, Database, FileText, Loader2, CheckCircle2 } from "lucide-react";

const STEP_CONFIG = {
  weather: { icon: Cloud, label: "Weather Forecast" },
  currency: { icon: ArrowLeftRight, label: "Currency Rates" },
  wikipedia: { icon: BookOpen, label: "Destination Info" },
  rag: { icon: Database, label: "Travel Knowledge" },
  itinerary: { icon: FileText, label: "Building Itinerary" },
};

export default function ProgressCards({ progress }) {
  if (!progress || progress.length === 0) return null;

  return (
    <div className="max-w-lg mx-auto space-y-3">
      <h2 className="text-xl font-semibold mb-4" style={{ color: "var(--color-primary)" }}>
        Researching your trip...
      </h2>
      {progress.map((p, i) => {
        const config = STEP_CONFIG[p.step] || { icon: Loader2, label: p.step };
        const Icon = config.icon;
        const isComplete = p.status === "complete";

        return (
          <div
            key={i}
            className="animate-fade-in flex items-center gap-3 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-4 py-3"
          >
            <Icon size={18} className={isComplete ? "text-green-600" : "text-[var(--color-accent)] animate-pulse"} />
            <span className="text-sm flex-1">{p.label || config.label}</span>
            {isComplete ? (
              <CheckCircle2 size={16} className="text-green-600" />
            ) : (
              <Loader2 size={16} className="text-[var(--color-accent)] animate-spin" />
            )}
          </div>
        );
      })}
    </div>
  );
}
