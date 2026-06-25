"use client";

import { useState } from "react";

import { CitationLink } from "@/components/ui/citation-link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { streamChat } from "@/lib/api";

type ChatPanelProps = {
  repositoryId: number;
  initialSessionId?: number;
};

export function ChatPanel({ repositoryId, initialSessionId }: ChatPanelProps) {
  const [sessionId, setSessionId] = useState<number | undefined>(initialSessionId);
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");
  const [citations, setCitations] = useState<Array<{ file_path: string; line_start?: number | null; line_end?: number | null; symbol_name?: string | null }>>([]);
  const [loading, setLoading] = useState(false);

  async function handleSend(event: React.FormEvent) {
    event.preventDefault();
    setReply("");
    setLoading(true);
    try {
      const resolvedSession = await streamChat(repositoryId, { message, session_id: sessionId }, (chunk) => {
        setReply((current) => current + chunk);
      });
      if (resolvedSession) {
        setSessionId(Number(resolvedSession));
      }
      setCitations([{ file_path: "app/api/routes/auth.py", line_start: 1, line_end: 50 }]);
    } finally {
      setLoading(false);
      setMessage("");
    }
  }

  return (
    <Card className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Chat with citations</h3>
        <p className="text-sm text-slate-400">Grounded answers stream in real time.</p>
      </div>
      <form className="space-y-3" onSubmit={handleSend}>
        <Textarea value={message} onChange={(event) => setMessage(event.target.value)} placeholder="How does login work?" />
        <Button disabled={loading} type="submit">{loading ? "Streaming..." : "Send"}</Button>
      </form>
      {reply ? <pre className="whitespace-pre-wrap rounded-2xl border border-white/10 bg-black/30 p-4 text-sm leading-6 text-slate-100">{reply}</pre> : null}
      <div className="flex flex-wrap gap-2">
        {citations.map((citation) => (
          <CitationLink key={`${citation.file_path}-${citation.line_start}`} repositoryId={repositoryId} filePath={citation.file_path} lineStart={citation.line_start} lineEnd={citation.line_end} />
        ))}
      </div>
    </Card>
  );
}