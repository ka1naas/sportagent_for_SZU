import { cn } from "@/lib/utils";

type ProgressStepsProps = {
  current: number;
  total: number;
};

export function ProgressSteps({ current, total }: ProgressStepsProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm text-muted">
        <span>规划进度</span>
        <span>
          Step {current} / {total}
        </span>
      </div>
      <div className="grid grid-cols-5 gap-2">
        {Array.from({ length: total }).map((_, index) => (
          <div
            key={index}
            className={cn(
              "h-2 rounded-full transition",
              index < current ? "bg-primary" : "bg-black/8",
            )}
          />
        ))}
      </div>
    </div>
  );
}
