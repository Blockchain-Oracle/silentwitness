import type { NextConfig } from "next";
import { createMDX } from "fumadocs-mdx/next";

const config: NextConfig = {
  reactStrictMode: true,
  // Static export for Vercel — Fumadocs + Pagefind both build at compile time,
  // no Node server needed at runtime. `output: 'export'` would force static
  // export, but we keep server mode so the search API route can stream
  // Pagefind results.
};

const withMDX = createMDX();
export default withMDX(config);
