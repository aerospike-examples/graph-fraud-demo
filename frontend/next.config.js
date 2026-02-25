/** @type {import('next').NextConfig} */

const backend = process.env.BACKEND_URL ?? "http://localhost:8080";
console.log(backend)
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
      {
        source: "/v3/api-docs",
        destination: `${backend}/v3/api-docs/fraud-detection`,
      },
      { source: '/v3/:path*', destination: `${backend}/v3/:path*` },
      { source: '/swagger-ui.html', destination: `${backend}/swagger-ui.html` },
      { source: '/swagger-ui/:path*', destination: `${backend}/swagger-ui/:path*` },
    ];
  },
};

module.exports = nextConfig;
