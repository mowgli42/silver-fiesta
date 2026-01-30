FROM alpine:latest

# Install NFS utilities and monitoring tools
RUN apk add --no-cache nfs-utils bash procps net-tools

# Create directory to share and log directory
RUN mkdir -p /data /var/log

# Copy exports configuration
COPY exports /etc/exports

# Expose NFS ports
EXPOSE 2049 111

# Startup script
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

CMD ["/usr/local/bin/start.sh"]
