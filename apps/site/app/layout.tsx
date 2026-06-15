import type { Metadata } from "next";
import type { ReactNode } from "react";
import { RootProvider } from "fumadocs-ui/provider/next";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "SilentWitness — hypothesis-first DFIR investigator",
    template: "%s · SilentWitness",
  },
  description:
    "MCP server + Pydantic AI agent that runs evidence-grounded, hash-chained, hypothesis-first DFIR investigations. Every claim locked to the tool execution that produced it.",
  metadataBase: new URL("https://silentwitness.vercel.app"),
  openGraph: {
    title: "SilentWitness — hypothesis-first DFIR investigator",
    description:
      "Open-source DFIR agent with architectural guardrails: entity gate, citation gate, hash-chained audit. 1838 tests, 88.39% coverage.",
    url: "https://silentwitness.vercel.app",
    siteName: "SilentWitness",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <RootProvider>{children}</RootProvider>
      </body>
    </html>
  );
}
