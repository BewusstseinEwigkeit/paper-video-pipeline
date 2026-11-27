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

// WebGL backend (light leaks, three.js scenes): ANGLE on Windows / macOS; software SwiftShader on Linux, where headless
// machines usually have no GPU. Override with PVP_GL=angle | swangle | egl | swiftshader | vulkan.
declare const process: { env: Record<string, string | undefined>; platform: string };
type GL = "angle" | "swangle" | "egl" | "swiftshader" | "vulkan" | "angle-egl";
Config.setChromiumOpenGlRenderer((process.env.PVP_GL as GL | undefined) ?? (process.platform === "linux" ? "swangle" : "angle"));
