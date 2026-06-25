"use client";

import { useEffect, useState } from "react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { LessonPlayer } from "@/components/onboarding/lesson-player";
import { Loading } from "@/components/ui/loading";
import { getOnboarding } from "@/lib/api";

export default function OnboardingPage({ params }: { params: { id: string } }) {
  const repositoryId = Number(params.id);
  const [bundle, setBundle] = useState<any>(null);

  useEffect(() => {
    getOnboarding(repositoryId).then(setBundle);
  }, [repositoryId]);

  return (
    <ProtectedRoute>
      <main className="min-h-screen bg-aurora px-6 py-10">
        <div className="mx-auto max-w-6xl">{!bundle ? <Loading label="Preparing onboarding lessons..." /> : <LessonPlayer lessons={bundle.lessons} />}</div>
      </main>
    </ProtectedRoute>
  );
}