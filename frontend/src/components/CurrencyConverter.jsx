import { useState } from "react";
import { ArrowLeftRight } from "lucide-react";

export default function CurrencyConverter({ currency }) {
  const [amount, setAmount] = useState("100");

  if (!currency) return null;

  const converted = (parseFloat(amount || "0") * currency.rate).toFixed(2);

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <ArrowLeftRight size={16} style={{ color: "var(--color-primary)" }} />
        <h3 className="font-semibold text-sm">Currency</h3>
        <span className="text-xs ml-auto" style={{ color: "var(--color-text-muted)" }}>
          1 {currency.from} = {currency.rate} {currency.to}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <label className="text-xs font-medium text-gray-500">{currency.from}</label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-full px-3 py-1.5 rounded-lg border border-[var(--color-border)] text-sm focus:outline-none focus:ring-1 focus:ring-[var(--color-primary-light)]"
          />
        </div>
        <ArrowLeftRight size={14} className="mt-4 text-gray-400" />
        <div className="flex-1">
          <label className="text-xs font-medium text-gray-500">{currency.to}</label>
          <div className="px-3 py-1.5 rounded-lg bg-gray-50 border border-[var(--color-border)] text-sm font-medium">
            {converted}
          </div>
        </div>
      </div>
    </div>
  );
}
