import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import MessageBubble from "./MessageBubble";

export default function ChatPanel({ messages, onSend, isProcessing, connected }) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;
    onSend(input.trim());
    setInput("");
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <h2 className="text-lg font-semibold" style={{ color: "var(--color-primary)" }}>
          Smart Travel Buddy
        </h2>
        <div className="flex items-center gap-1.5 text-xs">
          <div className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-red-400"}`} />
          <span style={{ color: "var(--color-text-muted)" }}>{connected ? "Connected" : "Disconnected"}</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="text-center mt-12" style={{ color: "var(--color-text-muted)" }}>
            <p className="text-lg mb-1">Where would you like to go?</p>
            <p className="text-sm">Tell me your dream destination and I'll plan the perfect trip.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} content={msg.content} />
        ))}
        {isProcessing && (
          <div className="flex justify-start mb-3">
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl rounded-bl-md px-4 py-2.5">
              <div className="flex gap-1">
                <span className="animate-pulse-dot w-1.5 h-1.5 rounded-full bg-[var(--color-text-muted)]" style={{ animationDelay: "0ms" }} />
                <span className="animate-pulse-dot w-1.5 h-1.5 rounded-full bg-[var(--color-text-muted)]" style={{ animationDelay: "300ms" }} />
                <span className="animate-pulse-dot w-1.5 h-1.5 rounded-full bg-[var(--color-text-muted)]" style={{ animationDelay: "600ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="px-4 py-3 border-t border-[var(--color-border)]">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Tell me about your trip..."
            disabled={!connected || isProcessing}
            className="flex-1 px-4 py-2.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary-light)] disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!connected || isProcessing || !input.trim()}
            className="px-4 py-2.5 rounded-xl text-white text-sm font-medium bg-[var(--color-primary)] hover:bg-[var(--color-primary-light)] disabled:opacity-50 transition-colors"
          >
            {isProcessing ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </div>
      </form>
    </div>
  );
}
