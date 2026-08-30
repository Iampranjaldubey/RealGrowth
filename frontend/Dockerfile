# Build stage
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json ./

# No lockfile is committed (see package.json comment); `npm install` resolves
# fresh. Every remaining dependency (react-router-dom, TanStack Query,
# chart.js) declares real React 19 peer support, so no --legacy-peer-deps
# escape hatch is needed — the previous Dockerfile needed it only because of
# react-simple-maps, which this rebuild replaced (see RankList.tsx).
RUN npm install

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