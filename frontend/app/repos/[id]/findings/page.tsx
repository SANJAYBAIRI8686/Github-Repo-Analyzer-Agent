"use client";

import { useEffect, useState } from "react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { Card } from "@/components/ui/card";
import { Loading } from "@/components/ui/loading";
import { getFindings } from "@/lib/api";

export default function FindingsPage({ params }: { params: { id: string } }) {
  const repositoryId = Number(params.id);
  const [bugs, setBugs] = useState<any>(null);
  const [security, setSecurity] = useState<any>(null);

  useEffect(() => {
    Promise.all([getFindings(repositoryId, "bugs"), getFindings(repositoryId, "security")]).then(([bugsData, securityData]) => {
      setBugs(bugsData);
      setSecurity(securityData);
    });
  }, [repositoryId]);

  return (
    <ProtectedRoute>
      <main className="min-h-screen bg-aurora px-6 py-10">
        <div className="mx-auto max-w-5xl space-y-6">
          {!bugs || !security ? <Loading label="Running analysis..." /> : null}
          {bugs && security ? (
            <div className="grid gap-6 md:grid-cols-2">
              {[{ title: "Bug Findings", data: bugs.findings }, { title: "Security Findings", data: security.findings }].map((section) => (
                <Card key={section.title}>
                  <h3 className="text-lg font-semibold">{section.title}</h3>
                  <div className="mt-3 space-y-3">
                    {section.data.map((finding: any) => (
                      <div key={`${finding.title}-${finding.file_path}-${finding.line}`} className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-white">{finding.title}</span>
                          <span className="text-xs text-accent2">{finding.severity}</span>
                        </div>
                        <div className="mt-1 text-slate-300">{finding.details}</div>
                        <div className="mt-1 text-xs text-slate-500">{finding.file_path}:{finding.line}</div>
                      </div>
                    ))}
                  </div>
                </Card>
              ))}
            </div>
          ) : null}
        </div>
      </main>
    </ProtectedRoute>
  );
}