import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatStars(value: number): string {
  return "★".repeat(Math.max(1, Math.round(value))) + "☆".repeat(Math.max(0, 5 - Math.round(value)));
}
