# ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
# ██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
# ██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
# ██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
# ██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
# ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
# Copyright (c) 2025 Rıza Emre ARAS

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    tor \
    iptables \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN echo "SOCKSPort 0.0.0.0:9050" >> /etc/tor/torrc && \
    echo "DNSPort 0.0.0.0:5353" >> /etc/tor/torrc && \
    echo "TransPort 0.0.0.0:9040" >> /etc/tor/torrc && \
    echo "ControlPort 0.0.0.0:9051" >> /etc/tor/torrc

COPY scripts/start-tor.sh /start-tor.sh
RUN chmod +x /start-tor.sh

CMD ["/start-tor.sh"]
