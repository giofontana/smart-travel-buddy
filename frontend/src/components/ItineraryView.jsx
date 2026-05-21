import DayCard from "./DayCard";
import PackingChecklist from "./PackingChecklist";
import CulturalTips from "./CulturalTips";
import CurrencyConverter from "./CurrencyConverter";
import { MapPin, Calendar } from "lucide-react";

export default function ItineraryView({ itinerary }) {
  if (!itinerary) return null;

  const startDate = itinerary.dates?.start
    ? new Date(itinerary.dates.start + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })
    : "";
  const endDate = itinerary.dates?.end
    ? new Date(itinerary.dates.end + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : "";

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="animate-fade-in bg-gradient-to-r from-blue-600 to-blue-800 text-white rounded-2xl p-6 mb-6">
        <h1 className="text-2xl font-bold mb-2">{itinerary.destination}</h1>
        <div className="flex items-center gap-4 text-blue-100 text-sm">
          <div className="flex items-center gap-1.5">
            <Calendar size={14} />
            <span>{startDate} — {endDate}</span>
          </div>
          {itinerary.currency && (
            <div className="flex items-center gap-1.5">
              <span>1 {itinerary.currency.from} = {itinerary.currency.rate} {itinerary.currency.to}</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex gap-6">
        {/* Day cards */}
        <div className="flex-1 space-y-4">
          {itinerary.days?.map((day, i) => (
            <DayCard key={i} day={day} dayNumber={i + 1} />
          ))}
        </div>

        {/* Sidebar widgets */}
        <div className="w-64 space-y-4 shrink-0">
          <CurrencyConverter currency={itinerary.currency} />
          <PackingChecklist items={itinerary.packing} />
          <CulturalTips tips={itinerary.cultural_tips} />
        </div>
      </div>
    </div>
  );
}
