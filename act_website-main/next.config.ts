import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  async redirects() {
    return [
      {
        source: "/:path*",
        has: [
          {
            type: "host",
            value: "www.airportandcitytransfer.com",
          },
        ],
        destination: "https://airportandcitytransfer.com/:path*",
        permanent: true,
      },
    ];
  },
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
