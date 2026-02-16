FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

FROM caddy:2-alpine

COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=5s \
    CMD wget -qO- http://localhost:80/ || exit 1
