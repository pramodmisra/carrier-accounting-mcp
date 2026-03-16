/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    // In dev, proxy API calls to the FastAPI backend
    // In production, Caddy handles routing
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
