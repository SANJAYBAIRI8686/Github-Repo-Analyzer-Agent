import { Card } from "@/components/ui/card";

export function FolderTree({ folders }: { folders: Record<string, string> }) {
  return (
    <Card>
      <h3 className="text-lg font-semibold">Folder Map</h3>
      <div className="mt-3 space-y-2 text-sm">
        {Object.entries(folders).map(([folder, summary]) => (
          <div key={folder} className="rounded-xl border border-white/10 bg-white/5 p-3">
            <div className="font-medium text-white">{folder}</div>
            <div className="text-slate-400">{summary}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}