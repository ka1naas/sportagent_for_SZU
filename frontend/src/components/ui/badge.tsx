import { cn } from "@/lib/utils";

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  tone?: "default" | "muted" | "success";
};

const toneClasses = {
  default: "bg-secondary text-secondary-foreground",
  muted: "bg-black/5 text-muted",
  success: "bg-[#dff7e8] text-[#256347]",
};

export function Badge({ className, tone = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn("inline-flex items-center rounded-full px-3 py-1 text-xs font-medium", toneClasses[tone], className)}
      {...props}
    />
  );
}
