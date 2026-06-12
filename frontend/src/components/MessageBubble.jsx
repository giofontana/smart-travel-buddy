import ThinkingBubble from "./ThinkingBubble";

function renderMarkdown(text) {
  const codeBlockRegex = /```(\w*)\n?([\s\S]*?)```/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", value: text.slice(lastIndex, match.index) });
    }
    parts.push({ type: "code", lang: match[1], value: match[2].trimEnd() });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push({ type: "text", value: text.slice(lastIndex) });
  }

  return parts.map((part, i) => {
    if (part.type === "code") {
      return (
        <pre key={i} className="my-2 p-3 rounded-lg text-xs overflow-x-auto"
          style={{ background: "var(--color-thinking)", fontFamily: "'JetBrains Mono', ui-monospace, monospace" }}>
          <code>{part.value}</code>
        </pre>
      );
    }
    return <span key={i} dangerouslySetInnerHTML={{ __html: inlineMarkdown(part.value) }} />;
  });
}

function inlineMarkdown(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, '<code style="background:var(--color-thinking);padding:1px 4px;border-radius:3px;font-size:0.85em">$1</code>')
    .replace(/\n/g, "<br/>");
}

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
              <div className="leading-relaxed">{isUser ? part.content : renderMarkdown(part.content)}</div>
            </div>
          ) : null
        )}
      </div>
    </div>
  );
}
