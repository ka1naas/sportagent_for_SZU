type SectionHeadingProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  align?: "left" | "center";
};

export function SectionHeading({ eyebrow, title, description, align = "left" }: SectionHeadingProps) {
  const alignClass = align === "center" ? "text-center items-center" : "text-left items-start";

  return (
    <div className={`flex flex-col gap-3 ${alignClass}`}>
      {eyebrow ? <span className="text-sm font-medium text-primary">{eyebrow}</span> : null}
      <div className="space-y-3">
        <h2 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl">{title}</h2>
        {description ? <p className="max-w-2xl text-base leading-7 text-muted">{description}</p> : null}
      </div>
    </div>
  );
}
