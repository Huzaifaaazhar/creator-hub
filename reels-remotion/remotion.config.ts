import path from "node:path";
/**
 * Note: When using the Node.JS APIs, the config file
 * doesn't apply. Instead, pass options directly to the APIs.
 *
 * All configuration options: https://remotion.dev/docs/config
 */

import { Config } from "@remotion/cli/config";

Config.setRspack(true);
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setDefaultPremountInSeconds(2);

// remocn components import each other through the "@/" alias in components.json.
// Bundlers don't read tsconfig paths, so the alias is resolved here as well.
// Both overrides are deliberate: the Remotion CLI applies overrideBundlerConfig
// with webpack and rspack alike, while Remocn Studio's preview reads only
// overrideWebpackConfig. Both run from the project root, which process.cwd()
// points at.
const withRemocnAlias = <C extends { resolve?: object }>(config: C): C => ({
  ...config,
  resolve: {
    ...config.resolve,
    alias: {
      ...((config.resolve as { alias?: object } | undefined)?.alias ?? {}),
      "@": path.join(process.cwd(), "src"),
    },
  },
});
// overrideBundlerConfig only exists in newer Remotion 4 releases.
if (typeof Config.overrideBundlerConfig === "function") {
  Config.overrideBundlerConfig(withRemocnAlias);
}
Config.overrideWebpackConfig(withRemocnAlias);
