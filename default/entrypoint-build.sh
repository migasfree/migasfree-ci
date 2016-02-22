#!/bin/bash

. build_packages.sh

_TARGET=/pub


build_dependences $_TARGET
build_migasfree_suite $_TARGET
build_repo_metadata $_TARGET
