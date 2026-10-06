import { ShieldCheck, ShieldOff } from "lucide-react";

export default function GuardrailsToggle({ enabled, available, onToggle }) {
  const on = enabled && available;
  const Icon = on ? ShieldCheck : ShieldOff;
  const title = !available
    ? "Guardrails not configured"
    : on
      ? "Guardrails on: messages are checked by NeMo Guardrails"
      : "Guardrails off: messages go straight to the model";

  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      onClick={onToggle}
      disabled={!available}
      title={title}
      className="flex items-center gap-1 px-2 py-1 rounded-full text-xs border transition-colors disabled:cursor-not-allowed disabled:opacity-50"
      style={{
        borderColor: on ? "var(--color-primary)" : "var(--color-border)",
        color: on ? "var(--color-primary)" : "var(--color-text-muted)",
      }}
    >
      <Icon className="w-3.5 h-3.5" />
      Guardrails {on ? "on" : "off"}
    </button>
  );
}
