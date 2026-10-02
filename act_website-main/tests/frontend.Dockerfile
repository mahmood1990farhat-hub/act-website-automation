FROM node:22-bookworm-slim
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=synthetic-not-a-real-key
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY . .
ARG ACT_TEST_FRENCH_PREVIEW=0
RUN --network=none if [ "$ACT_TEST_FRENCH_PREVIEW" = "1" ]; then node tests/check-language-foundation.cjs && node tests/check-french-drafts.cjs && node tests/prepare-french-preview.cjs; fi
RUN --network=none ./node_modules/.bin/tsc --noEmit && npm run build
RUN mkdir -p /app/.next/cache/images && chown -R node:node /app/.next/cache
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers
RUN npm install --prefix /opt/browser-test --ignore-scripts --no-audit --no-fund playwright@1.56.1 && /opt/browser-test/node_modules/.bin/playwright install --with-deps chromium && chmod -R a+rX /opt/playwright-browsers
RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-core && rm -rf /var/lib/apt/lists/*
USER node
CMD ["node", "tests/check-rendered-seo.cjs"]
