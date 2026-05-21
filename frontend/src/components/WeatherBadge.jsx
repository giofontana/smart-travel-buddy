export default function WeatherBadge({ weather }) {
  if (!weather) return null;

  const iconUrl = weather.icon
    ? `https://openweathermap.org/img/wn/${weather.icon}@2x.png`
    : null;

  return (
    <div className="flex items-center gap-2 bg-blue-50 rounded-lg px-3 py-1.5">
      {iconUrl && <img src={iconUrl} alt={weather.condition} className="w-8 h-8" />}
      <div className="text-xs">
        <div className="font-semibold text-blue-800">
          {weather.temp_high}° / {weather.temp_low}°
        </div>
        <div className="text-blue-600 capitalize">{weather.condition}</div>
      </div>
    </div>
  );
}
