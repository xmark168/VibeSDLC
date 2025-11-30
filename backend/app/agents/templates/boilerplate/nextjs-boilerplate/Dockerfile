# Build stage
FROM oven/bun:1 AS builder

WORKDIR /app

# Copy package files
COPY package.json bun.lock* ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy source code
COPY . .

# Generate Prisma client
RUN bunx prisma generate

# Build the application
RUN bun run build

# Production stage
FROM oven/bun:1-slim AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

# Copy built assets from builder
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules/.prisma ./node_modules/.prisma

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1

# Run the application
CMD ["bun", "run", "server.js"]
