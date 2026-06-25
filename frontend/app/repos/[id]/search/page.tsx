"use client";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { SearchPanel } from "@/components/search/search-panel";

export default function SearchPage({ params }: { params: { id: string } }) {
  return <ProtectedRoute><main className="min-h-screen bg-aurora px-6 py-10"><div className="mx-auto max-w-4xl"><SearchPanel repositoryId={Number(params.id)} /></div></main></ProtectedRoute>;
}