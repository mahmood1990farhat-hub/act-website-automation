import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  images: {
   remotePatterns:[{protocol:'http',hostname:'**'}, {
        protocol: 'https',
        hostname: '**',
      }, ]
  },
  // Allow large file downloads
  experimental: {
    serverActions: {
      bodySizeLimit: '100mb',
    },
  },
};

export default nextConfig;
