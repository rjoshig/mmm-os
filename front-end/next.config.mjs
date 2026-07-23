/** @type {import('next').NextConfig} */

// Proxy /api/* to the FastAPI backend so the browser never hits CORS in dev.
// Override the target with MMM_OS_API_URL. The front-end talks to the backend
// via this API — it never reads the backend database directly.
const API_TARGET = process.env.MMM_OS_API_URL || "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  // Emit a self-contained server bundle for a slim production container (Phase 11).
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_TARGET}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
