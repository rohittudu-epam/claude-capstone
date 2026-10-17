import type { NextConfig } from "next";

// In Docker/production the reverse proxy serves the UI and the API from one origin, so the browser calls
// relative /api paths and needs no rewrite. For `npm run dev` outside Docker, set API_PROXY_TARGET
// (for example http://localhost) to forward /api to the running backend through its proxy.
const apiProxyTarget = process.env.API_PROXY_TARGET;

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async rewrites() {
    return apiProxyTarget ? [{ source: "/api/:path*", destination: `${apiProxyTarget}/api/:path*` }] : [];
  },
};

export default nextConfig;
