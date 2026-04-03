# Stage 1: Build the static optimized application array
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Inject production environment arguments directly to the optimizer natively.
# The user's external browser will map exactly to port 8000 on the host wrapping the Docker service.
RUN echo "VITE_API_BASE_URL=http://localhost:8000/api/v1" > .env.production && \
    echo "VITE_WS_URL=ws://localhost:8000/api/v1" >> .env.production && \
    echo "VITE_MAPBOX_TOKEN=pk.eyJ1IjoicHJhdGlrcGFudGF3YW5lMTciLCJhIjoiY21uYTVlbWs1MGU5eTJwc2loMGd3dDMwayJ9.ehMRI21zo-pDNoE7r4mnxw" >> .env.production

RUN npm run build


# Stage 2: Serve standard HTTP requests efficiently using Alpine NGINX core
FROM nginx:alpine

# Purge default configurations
RUN rm -rf /usr/share/nginx/html/*

# Inherit static dist folder from Builder environment
COPY --from=builder /app/dist /usr/share/nginx/html

# Inherit the single-page application routing proxy hooks
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
