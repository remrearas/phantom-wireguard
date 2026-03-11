FROM mcr.microsoft.com/playwright:v1.58.2-noble

WORKDIR /app

# Docker CLI — allows tests to exec into sibling containers via mounted docker.sock
RUN apt-get update && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy test files and config
COPY tsconfig.json playwright.config.ts ./
COPY tests/ ./tests/

CMD ["sleep", "infinity"]
