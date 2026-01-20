FROM alpine:latest

# Install NFS utilities
RUN apk add --no-cache nfs-utils bash

# Create directory to share
RUN mkdir -p /data

# Copy exports configuration
COPY exports /etc/exports

# Expose NFS ports
EXPOSE 2049 111

# Startup script
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

CMD ["/usr/local/bin/start.sh"]
