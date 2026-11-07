# ==============================================================================
# DOCKERFILE CHO FRONTEND (REACT 19 + VITE + EXPRESS FULL-STACK RUNNER)
# ==============================================================================
# Multi-stage build tối ưu kích thước image và bảo mật môi trường production.

# Stage 1: Build Frontend Assets
FROM node:22-alpine AS builder

WORKDIR /app

# Sao chép package manifests và cài đặt toàn bộ dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Sao chép toàn bộ mã nguồn và thực hiện build bundle production
COPY . .
RUN npm run build

# Stage 2: Production Runtime
FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

# Chỉ cài đặt runtime dependencies
COPY package.json package-lock.json* ./
RUN npm install --omit=dev && npm install tsx

# Sao chép bundle tĩnh đã build từ builder
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/server.ts ./server.ts

# Expose cổng 3000 theo quy ước chuẩn
EXPOSE 3000

# Khởi chạy Express server proxy
CMD ["npx", "tsx", "server.ts"]
