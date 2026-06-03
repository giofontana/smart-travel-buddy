import { useState, useEffect, useRef, useCallback } from "react";

export function useTraceEvents(lastMessage) {
  const [events, setEvents] = useState([]);
  const [activeConnections, setActiveConnections] = useState([]);
  const [completedConnections, setCompletedConnections] = useState([]);
  const [startTime, setStartTime] = useState(null);
  const pendingStarts = useRef(new Map());

  const reset = useCallback(() => {
    setEvents([]);
    setActiveConnections([]);
    setCompletedConnections([]);
    setStartTime(Date.now());
    pendingStarts.current.clear();
  }, []);

  useEffect(() => {
    if (!lastMessage || lastMessage.type !== "trace") return;

    const evt = lastMessage;

    setEvents((prev) => [...prev].slice(-19).concat(evt));

    if (evt.status === "started") {
      if (!startTime) setStartTime(Date.now());
      const key = `${evt.source}->${evt.target}`;
      pendingStarts.current.set(key, evt.timestamp);
      setActiveConnections((prev) => [
        ...prev,
        { source: evt.source, target: evt.target, label: evt.label },
      ]);
    } else if (evt.status === "completed") {
      const key = `${evt.target}->${evt.source}`;
      pendingStarts.current.delete(key);
      setActiveConnections((prev) =>
        prev.filter(
          (c) => !(c.source === evt.target && c.target === evt.source)
        )
      );
      setCompletedConnections((prev) => [
        ...prev,
        {
          source: evt.source,
          target: evt.target,
          label: evt.label,
          duration_ms: evt.duration_ms,
        },
      ]);
    }
  }, [lastMessage, startTime]);

  return { events, activeConnections, completedConnections, startTime, reset };
}
