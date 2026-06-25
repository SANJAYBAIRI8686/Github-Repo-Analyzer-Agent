"use client";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { RepoSubmit } from "@/components/dashboard/repo-submit";
import { Card } from "@/components/ui/card";

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <main className="min-h-screen bg-aurora px-6 py-10">
        <div className="mx-auto max-w-6xl space-y-6">
          <Card>
            <h1 className="text-3xl font-semibold">Dashboard</h1>
            <p className="mt-2 text-slate-300">Submit a repository and watch ingestion progress before moving into chat, search, and documentation.</p>
          </Card>
          <RepoSubmit />
        </div>
      </main>
    </ProtectedRoute>
  );
}