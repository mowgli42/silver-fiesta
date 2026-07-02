.PHONY: test test-kernel test-lightweight test-standalone test-verbose clean config check-nfs-modules

COMPOSE ?= ./scripts/container-compose.sh
RUNTIME ?= $(shell command -v podman >/dev/null 2>&1 && echo podman || echo docker)

check-nfs-modules:
	@if [ ! -r /proc/fs/nfsd/version ] 2>/dev/null; then \
		echo "ERROR: NFS kernel modules are not loaded on this host."; \
		echo "       Load them with: sudo modprobe nfs nfsd"; \
		echo "       See README.md for persistent setup via /etc/modules-load.d/nfs.conf"; \
		exit 1; \
	fi

# Default: Use lightweight server (fastest, no build required)
test: check-nfs-modules test-lightweight

config:
	$(COMPOSE) config -q

test-lightweight:
	@$(COMPOSE) down --remove-orphans --volumes 2>&1 | grep -v "No resources" || true
	@$(RUNTIME) rm -f $$($(RUNTIME) ps -aq --filter "name=nfs" --filter "name=test-runner") 2>/dev/null || true
	$(COMPOSE) --profile default up --build --force-recreate --abort-on-container-exit

# Optional: Use kernel-based server (requires build, more full-featured)
test-kernel:
	NFS_SERVER=nfs-server NFS_SERVER_TYPE=kernel \
		$(COMPOSE) --profile kernel up --build --abort-on-container-exit

# Run tests with verbose NFS server logging
test-verbose:
	NFS_VERBOSE=true NFS_LOG_LEVEL=DEBUG \
		$(COMPOSE) --profile default up --build --abort-on-container-exit

test-standalone:
	sudo ./silver-fiesta $(NFS_SERVER)

probe:
	sudo ./silver-fiesta $(NFS_SERVER)

clean:
	$(COMPOSE) down -v --remove-orphans
	$(RUNTIME) network prune -f 2>/dev/null || true

