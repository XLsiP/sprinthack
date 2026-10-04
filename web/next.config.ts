import { existsSync } from "node:fs";
import { join } from "node:path";

import type { NextConfig } from "next";

/** The first of `names` present in public/partners/, as a URL path, or "" (see public/partners/README.md). */
function partnerFile(...names: string[]): string {
  const name = names.find((n) => existsSync(join(process.cwd(), "public", "partners", n)));
  return name ? `/partners/${name}` : "";
}

const nextConfig: NextConfig = {
  // Checked when the dev server or build starts, so every page agrees and a missing file is never requested.
  env: {
    BEACON_LOGO: partnerFile("beacon-logo.svg", "beacon-logo.png"),
    BEACON_ICON: partnerFile("beacon-icon.png"),
  },
};

export default nextConfig;
