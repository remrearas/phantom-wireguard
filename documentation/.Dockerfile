# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
# Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
#
# Phantom Documentation Kit Docker Image
FROM python:3.11-slim

COPY requirements.txt /tmp/requirements.txt
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg \
    git \
    build-essential python3 \
    libvips42 libvips-dev \
    libjpeg-dev libpng-dev libwebp-dev libgif-dev libtiff-dev \
    pkg-config autoconf automake libtool nasm && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    node --version && npm --version && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt