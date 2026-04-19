/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ['*.spock.replit.dev', '*.replit.dev'],
  turbopack: {
    resolveAlias: {
      // Shader file handling for Turbopack
    }
  },
  webpack: (config, { isServer }) => {
    // Exclude large data files from the file watcher to prevent OOM crashes
    config.watchOptions = {
      ...config.watchOptions,
      ignored: ['**/node_modules/**', '**/data/**', '**/.git/**', '**/*.log'],
    };
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
