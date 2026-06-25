"use client";

import { useState } from "react";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function LessonPlayer({ lessons }: { lessons: Array<{ slug: string; title: string; objective: string; summary: string; file_refs: string[]; checkpoint_question: string; checkpoint_hint: string }> }) {
  const [active, setActive] = useState(lessons[0]?.slug ?? "architecture");
  const lesson = lessons.find((item) => item.slug === active) ?? lessons[0];

  return (
    <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
      <Card className="space-y-2">
        {lessons.map((entry) => (
          <Button key={entry.slug} className={`w-full justify-start ${entry.slug === active ? "bg-accent" : "bg-white/5 text-white"}`} onClick={() => setActive(entry.slug)}>
            {entry.title}
          </Button>
        ))}
      </Card>
      <Card className="space-y-3">
        <h3 className="text-2xl font-semibold">{lesson.title}</h3>
        <p className="text-slate-300">{lesson.objective}</p>
        <p className="text-sm text-slate-400">{lesson.summary}</p>
        <div>
          <div className="text-sm font-medium text-white">File refs</div>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-300">
            {lesson.file_refs.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-slate-200">
          <div className="font-medium text-white">Checkpoint</div>
          <div>{lesson.checkpoint_question}</div>
          <div className="mt-2 text-xs text-slate-400">Hint: {lesson.checkpoint_hint}</div>
        </div>
      </Card>
    </div>
  );
}