FROM node:22-bookworm-slim
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=synthetic-not-a-real-key
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY . .
RUN --network=none npm run build
USER node
CMD ["node", "tests/check-rendered-seo.cjs"]
