import type { ReactNode } from "react";
import { DocsLayout } from "fumadocs-ui/layouts/docs";

import { source } from "@/lib/source";

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <DocsLayout
      tree={source.pageTree}
      nav={{
        title: (
          <span className="text-base font-bold tracking-tight">
            SilentWitness
          </span>
        ),
        // Search bar wired by Fumadocs RootProvider — see `app/layout.tsx`.
      }}
      themeSwitch={{
        enabled: false,
      }}
      sidebar={{
        defaultOpenLevel: 1,
      }}
    >
      {children}
    </DocsLayout>
  );
}
