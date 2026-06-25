import { Card } from "@/components/ui/card";
import { formatStars } from "@/lib/utils";

export function HealthCards({ categories, overall }: { categories: Array<{ name: string; score: number; max_score: number; stars: number; rationale: string; signals: string[] }>; overall: number }) {
  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-baseline justify-between">
          <div>
            <h3 className="text-lg font-semibold">Project Health</h3>
            <p className="text-sm text-slate-400">Overall score with rationale by category.</p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-white">{overall}/100</div>
            <div className="text-sm text-accent2">{formatStars(overall / 20)}</div>
          </div>
        </div>
      </Card>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {categories.map((category) => (
          <Card key={category.name}>
            <div className="flex items-center justify-between">
              <h4 className="font-semibold">{category.name}</h4>
              <span className="text-sm text-accent2">{category.score}/{category.max_score}</span>
            </div>
            <div className="mt-2 text-sm text-slate-300">{category.rationale}</div>
            <div className="mt-3 text-xs text-slate-500">{category.signals.join(" · ")}</div>
          </Card>
        ))}
      </div>
    </div>
  );
}