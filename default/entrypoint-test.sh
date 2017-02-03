#!/bin/bash

apt-get update
apt-get -y install gnupg2

apt-key add /pub/gpg_key
echo "deb file:///pub stable PKGS" > /etc/apt/sources.list.d/local.list

apt-key list

apt-get update
apt-get -y install migasfree-client
apt-get -y install migasfree-server

cat > /etc/migasfree.conf <<EOF
[client]
Version=TESTCASE

[packager]
User=packager
Password=packager
Version=TESTCASE
Store=org
EOF

DJANGO_SETTINGS_MODULE=migasfree.settings.production python /run-test.py
