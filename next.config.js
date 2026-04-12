/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config, { isServer }) => {
    config.module.rules.push({
      test: /\.(glsl|vs|fs|vert|frag)$/,
      exclude: /node_modules/,
      use: ['raw-loader']
    });
    return config;
  },
  experimental: {
    optimizePackageImports: ['sigma']
  }
};

module.exports = nextConfig;
