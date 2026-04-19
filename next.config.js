/** @type {import('next').NextConfig} */
const nextConfig = {
  turbopack: {
    resolveAlias: {
      // Shader file handling for Turbopack
    },
    // Exclude large data files from Turbopack processing
    contextIsolation: true,
  },
  webpack: (config, { isServer }) => {
    config.module.rules.push({
      test: /\.(glsl|vs|fs|vert|frag)$/,
      exclude: /node_modules/,
      use: ['raw-loader']
    });
    return config;
  },
  // Don't process these files
  pageExtensions: ['js', 'jsx', 'ts', 'tsx'],
  // Increase memory limit for build
  outputFileTracingRoot: './',
};

module.exports = nextConfig;
