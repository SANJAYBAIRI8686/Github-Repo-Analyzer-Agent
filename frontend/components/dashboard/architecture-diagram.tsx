import { Card } from "@/components/ui/card";

export function ArchitectureDiagram({ diagramSource }: { diagramSource: string }) {
  return (
    <Card>
      <h3 className="text-lg font-semibold">Architecture Diagram</h3>
      <pre className="mt-3 overflow-x-auto rounded-xl bg-black/30 p-4 text-xs text-slate-200">{diagramSource}</pre>
    </Card>
  );
}