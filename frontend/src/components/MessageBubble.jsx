import ThinkingBubble from "./ThinkingBubble";

function parseThinking(content) {
  const thinkRegex = /<think(?:ing)?>([\s\S]*?)<\/think(?:ing)?>/gi;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = thinkRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", content: content.slice(lastIndex, match.index) });
    }
    parts.push({ type: "thinking", content: match[1].trim() });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    parts.push({ type: "text", content: content.slice(lastIndex) });
  }

  return parts.length > 0 ? parts : [{ type: "text", content }];
}

export default function MessageBubble({ role, content }) {
  const isUser = role === "user";
  const parts = isUser ? [{ type: "text", content }] : parseThinking(content);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className="flex flex-col gap-1 max-w-[80%]">
        {parts.map((part, i) =>
          part.type === "thinking" ? (
            <ThinkingBubble key={i} content={part.content} />
          ) : part.content.trim() ? (
            <div
              key={i}
              className={`animate-fade-in rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                isUser
                  ? "bg-[var(--color-primary)] text-white rounded-br-md"
                  : "bg-[var(--color-surface)] border border-[var(--color-border)] rounded-bl-md"
              }`}
            >
              <div className="whitespace-pre-wrap">{part.content}</div>
            </div>
          ) : null
        )}
      </div>
    </div>
  );
}
