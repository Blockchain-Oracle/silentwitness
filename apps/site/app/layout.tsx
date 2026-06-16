import type { Metadata } from "next";
import type { ReactNode } from "react";
import { RootProvider } from "fumadocs-ui/provider/next";

import "./globals.css";

const siteUrl = "https://switness.xyz";

export const metadata: Metadata = {
  title: {
    default: "SilentWitness — hypothesis-first DFIR investigator",
    template: "%s · SilentWitness",
  },
  description:
    "MCP server + Pydantic AI agent that runs evidence-grounded, hash-chained, hypothesis-first DFIR investigations. Every claim locked to the tool execution that produced it.",
  metadataBase: new URL(siteUrl),
  openGraph: {
    title: "SilentWitness — hypothesis-first DFIR investigator",
    description:
      "Open-source DFIR agent with architectural guardrails: entity gate, citation gate, hash-chained audit. 1838 tests, 88.39% coverage.",
    url: siteUrl,
    siteName: "SilentWitness",
    images: [
      {
        url: "/brand/social-card.png",
        width: 924,
        height: 540,
        alt: "SilentWitness: prove every claim",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "SilentWitness — hypothesis-first DFIR investigator",
    description:
      "A Custom MCP Server submission for SANS Find Evil! 2026. Every claim is locked to the tool execution that produced it.",
    images: ["/brand/social-card.png"],
  },
  icons: {
    icon: "/brand/logo.svg",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="light" style={{ colorScheme: "light" }}>
      <body>
        <RootProvider theme={{ enabled: false }}>{children}</RootProvider>
      </body>
    </html>
  );
}
