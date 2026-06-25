"use client";

import { useState } from "react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function DocsViewer({ files, downloadUrl, onDownload }: { files: Array<{ filename: string; content: string }>; downloadUrl: string; onDownload: () => Promise<void> }) {
  const [active, setActive] = useState(files[0]?.filename ?? "README.md");
  const activeFile = files.find((file) => file.filename === active) ?? files[0];

  return (
    <div className="space-y-4">
      <Card className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold">Generated Docs</h3>
          <p className="text-sm text-slate-400">Rendered from the repository analysis.</p>
        </div>
        <Button onClick={onDownload}>Download ZIP</Button>
      </Card>
      <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
        <Card>
          <div className="space-y-2">
            {files.map((file) => (
              <button key={file.filename} className={`w-full rounded-xl border px-3 py-2 text-left text-sm ${file.filename === active ? "border-accent bg-accent/10" : "border-white/10 bg-white/5"}`} onClick={() => setActive(file.filename)}>
                {file.filename}
              </button>
            ))}
          </div>
        </Card>
        <Card>
          <pre className="whitespace-pre-wrap text-sm leading-6 text-slate-200">{activeFile?.content}</pre>
          <div className="mt-3 text-xs text-slate-500">Download path: {downloadUrl}</div>
        </Card>
      </div>
    </div>
  );
}