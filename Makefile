.PHONY: test test-kernel test-lightweight test-standalone test-verbose clean

# Default: Use lightweight server (fastest, no build required)
test: test-lightweight

test-lightweight:
	@docker-compose down --remove-orphans --volumes 2>&1 | grep -v "No resources" || true
	@docker rm -f $$(docker ps -aq --filter "name=nfs\|test-runner") 2>/dev/null || true
	docker-compose --profile default up --build --force-recreate --abort-on-container-exit

# Optional: Use kernel-based server (requires build, more full-featured)
test-kernel:
	NFS_SERVER=nfs-server NFS_SERVER_TYPE=kernel \
		docker-compose --profile kernel up --build --abort-on-container-exit

# Run tests with verbose NFS server logging
test-verbose:
	NFS_VERBOSE=true NFS_LOG_LEVEL=DEBUG \
		docker-compose --profile default up --build --abort-on-container-exit

test-standalone:
	./tests/standalone_test.sh $(NFS_SERVER)

clean:
	docker-compose down -v --remove-orphans
	docker network prune -f 2>/dev/null || true

