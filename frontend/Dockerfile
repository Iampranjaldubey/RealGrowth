# Build stage
FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./

# Use legacy-peer-deps to avoid conflicting React versions for the map library
RUN npm ci --legacy-peer-deps

COPY . .

# Pass in API URL at build time if needed
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Production stage - use unprivileged nginx
FROM nginxinc/nginx-unprivileged:alpine

COPY --from=build /app/dist /usr/share/nginx/html

# Add nginx config for React Router
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Non-root nginx listens on port 8080
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]