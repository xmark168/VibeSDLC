export default {
  seed: {
    engine: {
      binaryPath: 'node_modules/.bin/prisma',
    },
    runner: {
      run: 'tsx',
    },
    script: 'prisma/seed.ts',
  },
};
