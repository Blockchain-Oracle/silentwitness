// Fumadocs source loader. Reads the generated MDX index that `fumadocs-mdx`
// produces from `content/docs/` and exposes the standard Fumadocs `source`
// API used by the docs route + sidebar. This pattern mirrors story-cdr's
// `lib/source.ts` exactly.

import { loader } from "fumadocs-core/source";
import { docs } from "@/.source/server";

export const source = loader({
  baseUrl: "/docs",
  source: docs.toFumadocsSource(),
});
