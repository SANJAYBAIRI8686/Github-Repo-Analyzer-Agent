"use client";

import { useEffect, useState } from "react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { ArchitectureDiagram } from "@/components/dashboard/architecture-diagram";
import { DependencyList } from "@/components/dashboard/dependency-list";
import { FolderTree } from "@/components/dashboard/folder-tree";
import { HealthCards } from "@/components/dashboard/health-cards";
import { Card } from "@/components/ui/card";
import { Loading } from "@/components/ui/loading";
import { getArchitecture, getDependencies, getHealth, getOverview } from "@/lib/api";

export default function RepositoryPage({ params }: { params: { id: string } }) {
  const repositoryId = Number(params.id);
  const [overview, setOverview] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [architecture, setArchitecture] = useState<any>(null);
  const [dependencies, setDependencies] = useState<any>(null);

  useEffect(() => {
    Promise.all([getOverview(repositoryId), getHealth(repositoryId), getArchitecture(repositoryId), getDependencies(repositoryId)]).then(([overviewData, healthData, architectureData, dependencyData]) => {
      setOverview(overviewData);
      setHealth(healthData);
      setArchitecture(architectureData);
      setDependencies(dependencyData);
    });
  }, [repositoryId]);

  return (
    <ProtectedRoute>
      <main className="min-h-screen bg-aurora px-6 py-10">
        <div className="mx-auto max-w-6xl space-y-6">
          {!overview || !health || !architecture || !dependencies ? <Loading label="Loading repository intelligence..." /> : null}
          {overview && health && architecture && dependencies ? (
            <div className="space-y-6">
              <Card>
                <h1 className="text-3xl font-semibold">{overview.project_name ?? `Repository ${repositoryId}`}</h1>
                <p className="mt-2 text-slate-300">{overview.purpose}</p>
                <p className="mt-2 text-sm text-slate-400">{overview.architecture_summary}</p>
              </Card>
              <HealthCards categories={health.categories} overall={health.overall_score} />
              <ArchitectureDiagram diagramSource={architecture.diagram_source} />
              <FolderTree folders={overview.folder_explanations} />
              <DependencyList dependencies={dependencies.dependencies} />
            </div>
          ) : null}
        </div>
      </main>
    </ProtectedRoute>
  );
}