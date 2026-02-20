/** @type {import('next').NextConfig} */
const nextConfig = {
  // Needed so Three.js imports work cleanly in Next.js 14
  transpilePackages: ['three'],
  // Allow external font domains
  images: {
    domains: ['fonts.googleapis.com', 'fonts.gstatic.com'],
  },
}

module.exports = nextConfig
