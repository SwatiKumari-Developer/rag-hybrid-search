# Stage 1: Build React app
FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
# Multi-stage build keeps the final image small (just static files + nginx)
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config for React SPA (handles client-side routing)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
