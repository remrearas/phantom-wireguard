FROM mcr.microsoft.com/playwright:v1.58.2-noble

WORKDIR /app

# Docker CLI — static binary, no apt dependency on Ubuntu mirrors
RUN curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-27.5.1.tgz \
    | tar xz --strip-components=1 -C /usr/local/bin docker/docker

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy test files and config
COPY tsconfig.json playwright.config.ts ./
COPY tests/ ./tests/

CMD ["sleep", "infinity"]
