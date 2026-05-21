import { useState, useEffect, useCallback } from "react";
import { useWebSocket } from "./hooks/useWebSocket";
import ChatPanel from "./components/ChatPanel";
import ItineraryView from "./components/ItineraryView";
import ProgressCards from "./components/ProgressCards";

const WS_URL = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`;

export default function App() {
  const [messages, setMessages] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [itinerary, setItinerary] = useState(null);
  const [progress, setProgress] = useState([]);
  const [phase, setPhase] = useState("interview");

  const { connected, lastMessage, send } = useWebSocket(WS_URL);

  useEffect(() => {
    if (!lastMessage) return;

    switch (lastMessage.type) {
      case "agent_message":
        setMessages((prev) => [...prev, { role: "assistant", content: lastMessage.content }]);
        setIsProcessing(false);
        break;
      case "phase_change":
        setPhase(lastMessage.phase);
        break;
      case "progress":
        setProgress((prev) => {
          const existing = prev.findIndex((p) => p.step === lastMessage.step);
          if (existing >= 0) {
            const updated = [...prev];
            updated[existing] = lastMessage;
            return updated;
          }
          return [...prev, lastMessage];
        });
        break;
      case "itinerary":
        setItinerary(lastMessage.data);
        setProgress([]);
        setIsProcessing(false);
        break;
      case "error":
        setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${lastMessage.message}` }]);
        setIsProcessing(false);
        break;
    }
  }, [lastMessage]);

  const handleSend = useCallback(
    (content) => {
      setMessages((prev) => [...prev, { role: "user", content }]);
      setIsProcessing(true);
      send({ action: "message", content });
    },
    [send]
  );

  return (
    <div className="h-screen flex">
      {/* Left panel: Chat */}
      <div className="w-[400px] min-w-[350px] border-r border-[var(--color-border)] bg-[var(--color-bg)]">
        <ChatPanel
          messages={messages}
          onSend={handleSend}
          isProcessing={isProcessing}
          connected={connected}
        />
      </div>

      {/* Right panel: Itinerary / Progress */}
      <div className="flex-1 bg-[var(--color-bg)] overflow-y-auto p-6">
        {phase === "research" && progress.length > 0 && !itinerary && (
          <ProgressCards progress={progress} />
        )}

        {itinerary && <ItineraryView itinerary={itinerary} />}

        {!itinerary && progress.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center" style={{ color: "var(--color-text-muted)" }}>
              <p className="text-4xl mb-4">&#9992;&#65039;</p>
              <p className="text-lg font-medium">Your itinerary will appear here</p>
              <p className="text-sm mt-1">Start chatting to plan your trip</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
