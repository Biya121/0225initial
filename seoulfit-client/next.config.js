/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'image.musinsa.com' },
      { protocol: 'https', hostname: 'img.musinsa.com' },
      { protocol: 'https', hostname: 'cdn.musinsa.com' },
    ],
  },
};

module.exports = nextConfig;
