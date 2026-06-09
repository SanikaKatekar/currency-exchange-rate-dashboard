FROM node:20-alpine AS build

# VITE_API_KEY is baked into the bundle at build time (Vite replaces import.meta.env.VITE_*).
# Pass it via: docker compose build --build-arg VITE_API_KEY=<value>
# or set it in the build.args section of docker-compose.yml.
ARG VITE_API_KEY=""
ENV VITE_API_KEY=$VITE_API_KEY

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
