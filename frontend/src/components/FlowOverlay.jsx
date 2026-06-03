import { useState, useEffect } from "react";

function ComponentBox({ id, icon, label, activeConnections, completedConnections }) {
  const isSource = activeConnections.some((c) => c.source === id);
  const isTarget = activeConnections.some((c) => c.target === id);
  const isDone = completedConnections.some(
    (c) => c.source === id || c.target === id
  );

  let stateClass = "comp-idle";
  if (isTarget) stateClass = "comp-active";
  else if (isSource) stateClass = "comp-source";
  else if (isDone) stateClass = "comp-done";

  return (
    <div className={`flow-comp ${stateClass}`}>
      <span className="flow-comp-icon">{icon}</span>
      <span className="flow-comp-label">{label}</span>
      {isDone && !isTarget && !isSource && (
        <span className="flow-comp-check">{"✓"}</span>
      )}
    </div>
  );
}

function Arrow({ from, to, activeConnections }) {
  const isActive = activeConnections.some(
    (c) => c.source === from && c.target === to
  );

  return (
    <div className={`flow-arrow ${isActive ? "flow-arrow-active" : ""}`}>
      <span>{"→"}</span>
      {isActive && <span className="flow-dot" />}
    </div>
  );
}

function McpArrows({ activeConnections }) {
  const targets = ["mcp-weather", "mcp-currency", "mcp-wikipedia"];
  const anyActive = targets.some((t) =>
    activeConnections.some((c) => c.source === "backend" && c.target === t)
  );

  return (
    <div className="flow-mcp-arrows">
      {targets.map((t) => {
        const isActive = activeConnections.some(
          (c) => c.source === "backend" && c.target === t
        );
        return (
          <div
            key={t}
            className={`flow-arrow flow-arrow-sm ${isActive ? "flow-arrow-active" : anyActive ? "" : "flow-arrow-dim"}`}
          >
            <span>{"→"}</span>
            {isActive && <span className="flow-dot" />}
          </div>
        );
      })}
    </div>
  );
}

function TraceLog({ events }) {
  const recent = events.slice(-8);

  return (
    <div className="flow-log">
      <div className="flow-log-title">Trace Log</div>
      {recent.map((evt, i) => {
        const time = new Date(evt.timestamp * 1000).toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
        const isCompleted = evt.status === "completed";

        return (
          <div
            key={i}
            className={`flow-log-entry ${isCompleted ? "flow-log-done" : "flow-log-active"}`}
          >
            <span className="flow-log-time">{time}</span>
            <span className="flow-log-detail">
              {evt.source} {"→"} {evt.target}
            </span>
            <span className="flow-log-duration">
              {isCompleted && evt.duration_ms != null
                ? evt.duration_ms >= 1000
                  ? `${(evt.duration_ms / 1000).toFixed(1)}s`
                  : `${evt.duration_ms}ms`
                : "..."}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function ElapsedTimer({ startTime, endTime }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!startTime) return;
    if (endTime) {
      setElapsed(((endTime - startTime) / 1000).toFixed(1));
      return;
    }
    const interval = setInterval(() => {
      setElapsed(((Date.now() - startTime) / 1000).toFixed(1));
    }, 100);
    return () => clearInterval(interval);
  }, [startTime, endTime]);

  if (!startTime) return null;

  return (
    <div className="flow-timer">
      <span className="flow-timer-label">Elapsed</span>
      <span className="flow-timer-value">{elapsed}s</span>
    </div>
  );
}

export default function FlowOverlay({
  isOpen,
  events,
  activeConnections,
  completedConnections,
  startTime,
  endTime,
}) {
  if (!isOpen) return null;

  return (
    <div className="flow-overlay">
      <ElapsedTimer startTime={startTime} endTime={endTime} />

      <div className="flow-diagram">
        <ComponentBox id="user" icon={"\u{1F464}"} label="User"
          activeConnections={activeConnections} completedConnections={completedConnections} />
        <Arrow from="user" to="backend" activeConnections={activeConnections} />
        <ComponentBox id="backend" icon={"⚙️"} label="Backend"
          activeConnections={activeConnections} completedConnections={completedConnections} />
        <Arrow from="backend" to="llm" activeConnections={activeConnections} />
        <ComponentBox id="llm" icon={"\u{1F9E0}"} label="LLM"
          activeConnections={activeConnections} completedConnections={completedConnections} />
        <McpArrows activeConnections={activeConnections} />
        <div className="flow-mcp-group">
          <ComponentBox id="mcp-weather" icon={"\u{1F324}"} label="Weather"
            activeConnections={activeConnections} completedConnections={completedConnections} />
          <ComponentBox id="mcp-currency" icon={"\u{1F4B1}"} label="Currency"
            activeConnections={activeConnections} completedConnections={completedConnections} />
          <ComponentBox id="mcp-wikipedia" icon={"\u{1F4DA}"} label="Wikipedia"
            activeConnections={activeConnections} completedConnections={completedConnections} />
        </div>
        <Arrow from="backend" to="rag" activeConnections={activeConnections} />
        <ComponentBox id="rag" icon={"\u{1F5C4}️"} label="RAG"
          activeConnections={activeConnections} completedConnections={completedConnections} />
      </div>

      <TraceLog events={events} />
    </div>
  );
}
