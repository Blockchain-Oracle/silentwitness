import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import {
  ArrowRight,
  CheckCircle2,
  FileCheck2,
  GitBranch,
  LockKeyhole,
  Search,
  ShieldCheck,
  TerminalSquare,
} from "lucide-react";

const proofLinks = [
  {
    href: "/docs/quickstart",
    label: "Run it",
    title: "SIFT setup and first case",
    body: "Install the CLI, register evidence, investigate, review, verify, and export.",
    icon: <TerminalSquare className="h-5 w-5" />,
  },
  {
    href: "/docs/accuracy-report",
    label: "Measure it",
    title: "ROCBA accuracy report",
    body: "10 of 10 recalled in the headline run, with variance and misses documented.",
    icon: <CheckCircle2 className="h-5 w-5" />,
  },
  {
    href: "/docs/three-claim-trace",
    label: "Trace it",
    title: "Finding to tool execution",
    body: "Three claims traced from report observation to record, query audit row, and source artifact.",
    icon: <FileCheck2 className="h-5 w-5" />,
  },
  {
    href: "/docs/architecture",
    label: "Inspect it",
    title: "Guardrails in code",
    body: "Read-only evidence, MCP tool firewall, citation gate, entity gate, and hash-chain.",
    icon: <ShieldCheck className="h-5 w-5" />,
  },
];

const figures = [
  {
    src: "/brand/diagram-A-architecture.png",
    title: "Architecture",
    body: "Eight trust boundaries, six enforced in code.",
  },
  {
    src: "/brand/diagram-F-trace.png",
    title: "Claim Trace",
    body: "A finding has to resolve to the exact tool execution that produced it.",
  },
  {
    src: "/brand/card-self-correction.png",
    title: "Self-Correction",
    body: "Critic challenges and coverage-gate retries are visible in the audit logs.",
  },
];

export default function Landing() {
  return (
    <main className="min-h-screen bg-[color:var(--color-brand-paper)] text-[color:var(--color-brand-ink)]">
      <section className="relative isolate overflow-hidden bg-[color:var(--color-brand-night)] text-[color:var(--color-brand-paper)]">
        <Image
          src="/brand/social-card.png"
          alt=""
          width={924}
          height={540}
          priority
          className="absolute inset-0 -z-10 h-full w-full object-cover opacity-30"
        />
        <div className="absolute inset-0 -z-10 bg-[linear-gradient(90deg,rgba(19,23,24,0.96),rgba(19,23,24,0.80)_44%,rgba(19,23,24,0.48))]" />
        <div className="mx-auto flex min-h-[620px] max-w-6xl flex-col justify-center px-6 py-16">
          <div className="max-w-3xl">
            <p className="mb-5 flex items-center gap-2 text-sm font-semibold text-[color:var(--color-brand-mint)]">
              <LockKeyhole className="h-4 w-4" />
              SANS Find Evil! 2026 · Custom MCP Server submission
            </p>
            <h1 className="text-5xl font-extrabold leading-[1.02] sm:text-6xl">
              SilentWitness
            </h1>
            <p className="mt-6 max-w-2xl text-xl leading-8 text-[color:var(--color-brand-paper)]/82">
              A hypothesis-first DFIR investigator whose report writes itself, with every
              claim locked to the tool execution that produced it.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link className="sw-button sw-button-primary" href="/docs/quickstart">
                Start with setup <ArrowRight className="h-4 w-4" />
              </Link>
              <Link className="sw-button sw-button-secondary" href="/docs/three-claim-trace">
                Review the trace <Search className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-[color:var(--color-brand-line)] bg-white">
        <div className="mx-auto grid max-w-6xl gap-px px-6 py-6 sm:grid-cols-3">
          <Metric value="10/10" label="ROCBA findings recalled in the headline run" />
          <Metric value="12" label="agent-visible MCP tools, no generic shell surface" />
          <Metric value="1,838" label="unit, integration, and property tests" />
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="mb-3 text-sm font-semibold text-[color:var(--color-brand-forest)]">
              Judge path
            </p>
            <h2 className="max-w-2xl text-3xl font-bold leading-tight">
              The shortest route from submission review to evidence.
            </h2>
          </div>
          <Link
            className="inline-flex items-center gap-2 text-sm font-semibold text-[color:var(--color-brand-indigo)]"
            href="/docs"
          >
            Open all docs <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {proofLinks.map((item) => (
            <Link
              className="group flex min-h-[210px] flex-col justify-between rounded-lg border border-[color:var(--color-brand-line)] bg-white p-5 transition hover:border-[color:var(--color-brand-forest)] hover:shadow-[0_14px_32px_-24px_rgba(19,23,24,0.5)]"
              href={item.href}
              key={item.href}
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-md bg-[color:var(--color-brand-mint-soft)] text-[color:var(--color-brand-forest)]">
                {item.icon}
              </span>
              <span>
                <span className="text-xs font-semibold uppercase text-[color:var(--color-brand-forest)]">
                  {item.label}
                </span>
                <h3 className="mt-2 text-lg font-semibold leading-snug">{item.title}</h3>
                <p className="mt-2 text-sm leading-6 text-[color:var(--color-brand-muted)]">
                  {item.body}
                </p>
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="bg-[color:var(--color-brand-cream)]">
        <div className="mx-auto grid max-w-6xl gap-8 px-6 py-16 lg:grid-cols-[0.86fr_1.14fr] lg:items-center">
          <div>
            <p className="mb-3 text-sm font-semibold text-[color:var(--color-brand-rust)]">
              Constraint implementation
            </p>
            <h2 className="text-3xl font-bold leading-tight">
              The model plans. The server decides what can become evidence.
            </h2>
            <p className="mt-5 text-base leading-7 text-[color:var(--color-brand-muted)]">
              SilentWitness keeps raw evidence behind a read-only mount and exposes only
              typed MCP tools. Citation and entity gates run before an observation is
              recorded, so unsupported claims fail at the tool boundary instead of being
              cleaned up later in prose.
            </p>
            <div className="mt-7 grid gap-3">
              <Guardrail icon={<GitBranch className="h-4 w-4" />} text="Hypotheses form, pivot, confirm, or abandon in the audit log." />
              <Guardrail icon={<ShieldCheck className="h-4 w-4" />} text="Prompt-based guidance is supplementary, not the security boundary." />
              <Guardrail icon={<FileCheck2 className="h-4 w-4" />} text="Every report claim can be traced to a record, audit row, and source artifact." />
            </div>
          </div>
          <Image
            src="/brand/firewall-animated-still.png"
            alt="SilentWitness hallucination firewall showing staged claim checks"
            width={924}
            height={540}
            loading="eager"
            className="w-full rounded-lg border border-[color:var(--color-brand-line)] bg-white"
          />
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="mb-8">
          <p className="mb-3 text-sm font-semibold text-[color:var(--color-brand-forest)]">
            Visual evidence
          </p>
          <h2 className="max-w-2xl text-3xl font-bold leading-tight">
            Architecture images are part of the review packet.
          </h2>
        </div>
        <div className="grid gap-5 lg:grid-cols-3">
          {figures.map((figure) => (
            <figure
              className="overflow-hidden rounded-lg border border-[color:var(--color-brand-line)] bg-white"
              key={figure.src}
            >
              <Image
                src={figure.src}
                alt={figure.title}
                width={924}
                height={540}
                loading="eager"
                className="aspect-[77/45] w-full object-cover"
              />
              <figcaption className="p-5">
                <h3 className="font-semibold">{figure.title}</h3>
                <p className="mt-2 text-sm leading-6 text-[color:var(--color-brand-muted)]">
                  {figure.body}
                </p>
              </figcaption>
            </figure>
          ))}
        </div>
      </section>
    </main>
  );
}

function Metric({ value, label }: { value: string; label: string }) {
  return (
    <div className="px-0 py-4 sm:px-6">
      <div className="text-3xl font-bold text-[color:var(--color-brand-indigo)]">{value}</div>
      <div className="mt-1 text-sm leading-6 text-[color:var(--color-brand-muted)]">{label}</div>
    </div>
  );
}

function Guardrail({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <div className="flex items-start gap-3 border-l-2 border-[color:var(--color-brand-forest)] bg-white px-4 py-3">
      <span className="mt-1 text-[color:var(--color-brand-forest)]">{icon}</span>
      <p className="text-sm leading-6 text-[color:var(--color-brand-muted)]">{text}</p>
    </div>
  );
}
