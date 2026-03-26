# ---- Build stage ----
FROM node:20-alpine AS builder
WORKDIR /app

# Install build deps for better-sqlite3 (native module)
RUN apk add --no-cache python3 make g++

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- Production stage ----
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# Runtime dep for better-sqlite3
RUN apk add --no-cache libstdc++

# Next.js standalone output
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Schema file needed at runtime by the DB init code
COPY --from=builder /app/src/lib/db/schema.sql ./src/lib/db/schema.sql

# Frontend SQLite DB and recordings live here — mount as volume
RUN mkdir -p public/recordings

EXPOSE 3000

CMD ["node", "server.js"]
