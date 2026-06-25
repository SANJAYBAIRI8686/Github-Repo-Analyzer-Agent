"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { submitRepository, getJob } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function RepoSubmit() {
  const router = useRouter();
  const [url, setUrl] = useState("https://github.com/fastapi/fastapi");
  const [branch, setBranch] = useState("main");
  const [job, setJob] = useState<{ id: number; progress_pct: number; status: string; stage: string | null } | null>(null);
  const [message, setMessage] = useState<string>("");

  async function poll(jobId: number) {
    const tick = async () => {
      const response = await getJob(jobId);
      setJob(response.job);
      if (response.job.status === "completed") {
        setMessage("Ingestion complete.");
        router.push(`/repos/${response.job.repository_id}`);
        return;
      }
      if (response.job.status === "failed") {
        setMessage(response.job.error || "Ingestion failed");
        return;
      }
      setTimeout(tick, 1500);
    };
    await tick();
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setMessage("Submitting repository...");
    const response = await submitRepository(url, branch, true);
    setMessage(`Job ${response.job_id} queued`);
    setJob({ id: response.job_id, progress_pct: 0, status: "queued", stage: "queued" });
    await poll(response.job_id);
  }

  return (
    <Card className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Submit Repository</h2>
        <p className="text-sm text-slate-400">Clone a GitHub repo and watch ingestion progress live.</p>
      </div>
      <form className="grid gap-3 md:grid-cols-[1fr_180px_auto]" onSubmit={handleSubmit}>
        <Input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://github.com/owner/repo" />
        <Input value={branch} onChange={(event) => setBranch(event.target.value)} placeholder="Branch" />
        <Button type="submit">Submit</Button>
      </form>
      <div className="space-y-2">
        <div className="h-3 overflow-hidden rounded-full bg-white/10">
          <div className="h-full rounded-full bg-gradient-to-r from-accent to-accent2 transition-all" style={{ width: `${job?.progress_pct ?? 0}%` }} />
        </div>
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>{job?.status ?? "idle"}</span>
          <span>{job?.stage ?? "waiting"}</span>
        </div>
        {message ? <p className="text-sm text-slate-200">{message}</p> : null}
      </div>
    </Card>
  );
}