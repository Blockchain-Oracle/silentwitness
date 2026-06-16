import { defineDocs, defineConfig, frontmatterSchema } from "fumadocs-mdx/config";
import { z } from "zod";

export const docs = defineDocs({
  dir: "content/docs",
  docs: {
    schema: frontmatterSchema.extend({
      // Optional cross-link metadata the docs layout reads to render
      // breadcrumbs and prev/next nav without us hand-wiring per page.
      breadcrumb: z.array(z.string()).optional(),
      prev: z.object({ href: z.string(), label: z.string() }).optional(),
      next: z.object({ href: z.string(), label: z.string() }).optional(),
    }),
  },
});

export default defineConfig();
