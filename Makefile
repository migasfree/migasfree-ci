#include env_make

all: build test
.PHONY: all

build:
	./bin/build
	
test:
	./bin/test
    
push:
	./bin/push
   
	
