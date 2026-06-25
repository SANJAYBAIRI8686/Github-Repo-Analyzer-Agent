import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-aurora px-6 py-14 text-white">
      <div className="mx-auto flex max-w-5xl flex-col gap-8">
        <section className="max-w-3xl space-y-5">
          <div className="inline-flex rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.3em] text-accent2">GitHub Repo Analyzer</div>
          <h1 className="text-5xl font-semibold leading-tight">Understand a repository, then teach it to the next person.</h1>
          <p className="max-w-2xl text-lg text-slate-300">Upload a repo, watch ingestion progress, chat with grounded citations, inspect health, generate docs, and walk through onboarding lessons.</p>
          <div className="flex gap-3">
            <Link className="rounded-xl bg-accent px-5 py-3 font-semibold text-ink" href="/register">Create account</Link>
            <Link className="rounded-xl border border-white/15 bg-white/5 px-5 py-3 font-semibold" href="/login">Login</Link>
          </div>
        </section>
      </div>
    </main>
  );
}