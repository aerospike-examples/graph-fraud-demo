/** @type {import('next').NextConfig} */

const backend = "http://localhost:4000"

const nextConfig = {
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: `${backend}/:path*`,
            }
        ]
    },
}

module.exports = nextConfig 