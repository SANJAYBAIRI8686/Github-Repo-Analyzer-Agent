"use client";

import { useEffect, useState } from "react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { DocsViewer } from "@/components/docs/docs-viewer";
import { Loading } from "@/components/ui/loading";
import { downloadDocsZip, generateDocs } from "@/lib/api";

export default function DocsPage({ params }: { params: { id: string } }) {
  const repositoryId = Number(params.id);
  const [bundle, setBundle] = useState<any>(null);

  useEffect(() => {
    generateDocs(repositoryId).then(setBundle);
  }, [repositoryId]);

  return (
    <ProtectedRoute>
      <main className="min-h-screen bg-aurora px-6 py-10">
        <div className="mx-auto max-w-6xl">
          {!bundle ? <Loading label="Generating docs..." /> : <DocsViewer files={bundle.files} downloadUrl={bundle.download_url} onDownload={async () => { const blob = await downloadDocsZip(repositoryId); const url = URL.createObjectURL(blob); window.open(url, "_blank"); }} />}
        </div>
      </main>
    </ProtectedRoute>
  );
}