FROM python:3.9-slim

# Install NFS client tools
RUN apt-get update && \
    apt-get install -y nfs-common iputils-ping && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy test code and runner
COPY . .
RUN chmod +x run_tests.sh generate_performance_report.py diagnose_failures.py preflight_check.py cli.py

# Create mount point
RUN mkdir -p /mnt/nfs

CMD ["bash", "run_tests.sh"]
