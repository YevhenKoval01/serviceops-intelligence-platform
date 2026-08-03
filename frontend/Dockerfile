FROM node:22.15.1-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27.5-alpine
ENV BACKEND_SCHEME=http \
    BACKEND_HOST=backend \
    BACKEND_PORT=8080 \
    NGINX_ENVSUBST_FILTER="^(BACKEND_SCHEME|BACKEND_HOST|BACKEND_PORT)$"
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
