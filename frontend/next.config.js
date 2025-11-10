/** @type {import('next').NextConfig} */

const backend = process.env.BACKEND_URL ?? "http://localhost:8080";

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
      {
        source: "/v3/api-docs",
        destination: `${backend}/v3/api-docs`,
      },
    ];
  },
};

module.exports = nextConfig;
