import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-2xl border border-white/10 bg-panel/85 p-4 shadow-glow backdrop-blur", className)} {...props} />;
}