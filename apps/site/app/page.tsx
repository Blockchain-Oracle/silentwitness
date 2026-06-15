import Link from "next/link";
import { ArrowRight, Lock, Search, ShieldCheck } from "lucide-react";

export default function Landing() {
  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-16 px-6 py-20">
      <section className="flex flex-col gap-6">
        <p className="text-sm font-medium uppercase tracking-[0.18em] text-[color:var(--color-brand-forest)]">
          SANS Find Evil! 2026 · Hackathon submission
        </p>
        <h1 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
          SilentWitness — a hypothesis-first DFIR investigator whose report writes itself,
          with every claim locked to the tool that produced it.
        </h1>
        <p className="max-w-3xl text-lg text-[color:var(--color-brand-ink)]/80">
          MCP server plus Pydantic AI agent. Architectural guardrails — entity gate,
          citation gate, corroboration tier, hash-chained audit — sit in code, not in
          prompts. Coverage gate enforces all five key questions before the agent can
          terminate. <strong>Result on the real ROCBA case: 10 of 10 ground-truth
          findings recalled.</strong>
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/docs"
            className="inline-flex items-center gap-2 rounded-md bg-[color:var(--color-brand-indigo)] px-5 py-2.5 text-sm font-semibold text-[color:var(--color-brand-beige-soft)] transition hover:opacity-90"
          >
            Read the docs <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href="https://github.com/Blockchain-Oracle/silentwitness"
            className="inline-flex items-center gap-2 rounded-md border border-[color:var(--color-brand-ink)]/15 bg-[color:var(--color-brand-beige)] px-5 py-2.5 text-sm font-semibold text-[color:var(--color-brand-ink)] transition hover:bg-[color:var(--color-brand-beige)]/70"
          >
            View on GitHub
          </a>
        </div>
      </section>

      <section className="grid gap-6 sm:grid-cols-3">
        <Feature
          icon={<ShieldCheck className="h-5 w-5" />}
          title="Architectural guardrails"
          body="Entity gate + citation gate + corroboration tier run in code. Prompts are supplementary — removing them degrades quality but cannot unlock hallucinations against unmounted artifacts."
        />
        <Feature
          icon={<Lock className="h-5 w-5" />}
          title="Hash-chained audit"
          body="Every audit row carries record_hash + prev_record_hash. silentwitness verify --audit-chain walks every backend and reports any break, with file:line precision."
        />
        <Feature
          icon={<Search className="h-5 w-5" />}
          title="5-Key-Questions coverage"
          body="Output validator raises ModelRetry until WHO / WHAT / WHEN / WHERE / HOW are all answered. Live critic CHALLENGEs hypotheses before observations are committed."
        />
      </section>

      <footer className="border-t border-[color:var(--color-brand-ink)]/15 pt-8 text-sm text-[color:var(--color-brand-ink)]/65">
        MIT licensed. 1838 tests · 88.39% line coverage. Built for{" "}
        <a
          className="underline"
          href="https://findevil.devpost.com/"
          target="_blank"
          rel="noreferrer"
        >
          SANS Find Evil! 2026
        </a>
        .
      </footer>
    </main>
  );
}

function Feature({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-lg border border-[color:var(--color-brand-ink)]/12 bg-[color:var(--color-brand-beige)] p-6">
      <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-md bg-[color:var(--color-brand-indigo)]/10 text-[color:var(--color-brand-indigo)]">
        {icon}
      </div>
      <h2 className="mb-2 text-base font-semibold">{title}</h2>
      <p className="text-sm leading-relaxed text-[color:var(--color-brand-ink)]/75">
        {body}
      </p>
    </div>
  );
}
