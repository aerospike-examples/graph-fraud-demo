/** @type {import('next').NextConfig} */

const backend = process.env.BACKEND_URL ?? "http://localhost:4000"
const zipkin = process.env.ZIPKIN_URL ?? "http://localhost:9411"

const nextConfig = {
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: `${backend}/:path*`,
            },
            {
                source: '/zipkin/:path*',
                destination: `${zipkin}/zipkin/:path*`,
            }
        ]
    },
}

module.exports = nextConfig 