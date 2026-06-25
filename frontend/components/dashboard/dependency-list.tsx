import { Card } from "@/components/ui/card";

export function DependencyList({ dependencies }: { dependencies: Array<{ name: string; spec: string | null; description: string; why_used: string; source_file: string | null }> }) {
  return (
    <Card>
      <h3 className="text-lg font-semibold">Dependencies</h3>
      <div className="mt-3 space-y-3">
        {dependencies.map((dependency) => (
          <div key={`${dependency.name}-${dependency.spec ?? "latest"}`} className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="font-medium text-white">{dependency.name}</span>
              <span className="text-xs text-slate-400">{dependency.spec ?? "latest"}</span>
            </div>
            <p className="mt-1 text-slate-300">{dependency.description}</p>
            <p className="mt-1 text-xs text-accent2">Why: {dependency.why_used}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}