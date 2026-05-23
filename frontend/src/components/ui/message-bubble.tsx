import { cn } from "@/lib/utils";

type MessageBubbleProps = {
  role: "assistant" | "user";
  title?: string;
  content: string;
};

export function MessageBubble({ role, title, content }: MessageBubbleProps) {
  const isAssistant = role === "assistant";

  return (
    <div className={cn("flex", isAssistant ? "justify-start" : "justify-end")}>
      <div
        className={cn(
          "max-w-[85%] rounded-[24px] px-5 py-4 shadow-soft",
          isAssistant ? "bg-white text-foreground" : "bg-primary text-primary-foreground",
        )}
      >
        {title ? <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] opacity-70">{title}</p> : null}
        <p className="text-sm leading-7">{content}</p>
      </div>
    </div>
  );
}
