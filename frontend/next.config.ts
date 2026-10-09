import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server bundle for a small production Docker image.
  output: "standalone",
  poweredByHeader: false,
  // Keep the dev-only Next.js badge off the sidebar's organisation card.
  devIndicators: { position: "bottom-right" },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(self)" },
        ],
      },
    ];
  },
};

export default nextConfig;
