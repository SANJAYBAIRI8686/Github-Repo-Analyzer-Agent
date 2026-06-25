"use client";

import { useState } from "react";

import { searchRepository } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function SearchPanel({ repositoryId }: { repositoryId: number }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Array<{ file_path: string | null; snippet: string; citation: string }>>([]);
  const [loading, setLoading] = useState(false);

  async function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    try {
      const response = await searchRepository(repositoryId, query);
      setResults(response.hits);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="space-y-4">
      <form className="flex gap-3" onSubmit={handleSearch}>
        <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Where is Stripe used?" />
        <Button type="submit">{loading ? "Searching..." : "Search"}</Button>
      </form>
      <div className="space-y-3">
        {results.map((result) => (
          <div key={result.citation} className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm">
            <div className="font-medium text-white">{result.file_path}</div>
            <div className="mt-1 text-slate-300">{result.snippet}</div>
            <div className="mt-1 text-xs text-accent2">{result.citation}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}