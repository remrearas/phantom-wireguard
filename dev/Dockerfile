# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
#
# firewall-bridge development container
# Full Linux environment: Rust + nftables + iproute2 + Python + pytest
#
# Usage:
#   dev/build.sh          # build image
#   dev/shell.sh          # interactive shell (source mounted)
#   dev/cargo.sh test     # run cargo commands inside container
#   dev/pytest.sh         # run Python tests inside container

FROM rust:1.85-bookworm

# System dependencies: nftables (build + runtime) + networking tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnftables-dev libmnl-dev \
    nftables iproute2 iptables iputils-ping procps \
    python3 python3-pip python3-venv \
    sqlite3 bash \
    && rm -rf /var/lib/apt/lists/*

# Python test dependencies
RUN pip3 install --break-system-packages pytest==9.0.2 pytest-cov==7.0.0

# Rust cache directory
ENV CARGO_HOME=/cargo
ENV PATH="/cargo/bin:${PATH}"

WORKDIR /workspace

# Pre-fetch dependencies for faster rebuilds
COPY Cargo.toml Cargo.lock /workspace/
RUN mkdir -p src && echo "// stub" > src/lib.rs && cargo fetch && rm -rf src

CMD ["bash"]
