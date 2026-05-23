import Link from "next/link";
import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  asChild?: boolean;
  href?: string;
};

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-primary text-primary-foreground shadow-soft hover:bg-[#1f5f55]",
  secondary: "bg-secondary text-secondary-foreground hover:bg-[#d3ebe4]",
  ghost: "bg-transparent text-foreground hover:bg-black/5",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-10 px-4 text-sm",
  md: "h-11 px-5 text-sm",
  lg: "h-12 px-6 text-base",
};

export function Button({ className, variant = "primary", size = "md", asChild = false, href, children, ...props }: ButtonProps) {
  if (asChild && href) {
    return (
      <Link
        href={href}
        className={cn(
          "inline-flex items-center justify-center rounded-full font-medium transition duration-200 focus:outline-none focus:ring-2 focus:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-60",
          variantClasses[variant],
          sizeClasses[size],
          className,
        )}
      >
        {children}
      </Link>
    );
  }

  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-full font-medium transition duration-200 focus:outline-none focus:ring-2 focus:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-60",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
