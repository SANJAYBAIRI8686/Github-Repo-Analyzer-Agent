export function Loading({ label = "Loading..." }: { label?: string }) {
  return <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300">{label}</div>;
}