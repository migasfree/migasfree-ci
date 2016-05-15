#include env_make

all: build test test-docker
.PHONY: all

build:
	./bin/build

test:
	./bin/test

test-docker:
	./bin/test-docker

push:
	./bin/push

