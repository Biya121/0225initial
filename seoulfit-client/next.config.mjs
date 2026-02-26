/** @type {import('next').NextConfig} */
const nextConfig = {
  // React StrictMode 끄기 — useEffect 중복 호출 방지
  reactStrictMode: false,
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'image.msscdn.net' },
      { protocol: 'https', hostname: 'image.musinsa.com' },
      { protocol: 'https', hostname: 'img.musinsa.com' },
      { protocol: 'https', hostname: 'cdn.musinsa.com' },
      { protocol: 'https', hostname: 'static.musinsa.com' },
    ],
  },
  serverExternalPackages: ['puppeteer'],
};

export default nextConfig;
