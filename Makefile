.PHONY: test test-kernel test-lightweight test-standalone clean

test: test-kernel

test-kernel:
	docker-compose --profile kernel up --build --abort-on-container-exit

test-lightweight:
	NFS_SERVER=nfs-server-lightweight NFS_SERVER_TYPE=lightweight \
		docker-compose --profile lightweight up --build --abort-on-container-exit

test-standalone:
	./tests/standalone_test.sh $(NFS_SERVER)

clean:
	docker-compose down -v

