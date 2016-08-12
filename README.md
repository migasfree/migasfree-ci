# migasfree-ci

Provides Continuous Integration for migasfree.

We use two types images docker:

* ci-build, used to build the packages and put in a local repository (/pub)

* ci-test, used to install from a docker image base the migasfree apps and run a integrity test.


## Build and Test

```sh
make
```

### Environment
* **_GIT** Path to a local git repository with the projects: migasfree, migasfree-client and/or migasfree-launcher. If this variable is not set assume lastest version in github.

* **_TEST_FROM** To run test in a set of distros. If not is set, assume ubuntu:trusty, ubuntu:xenial, debian:jessie and debian:stretch

Sample:
```sh
_GIT=/home/tux/git _TEST_FROM="ubuntu:trusty debian:jessie" make
```

## Only build the packages

Samples:

```sh
make build
```

```sh
_GIT=/home/tux/git make build
```

## Only run integrity test

Sample:
```sh
make test
```

## Push packages to migasfree.org/pub

```sh
make push
```

