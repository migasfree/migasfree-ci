#!/bin/bash

#wget -O - http://migasfree.org/pub/gpg_key | apt-key add -
#echo "deb http://migasfree.org/pub wheezy PKGS" > /etc/apt/sources.list.d/local.list

apt-key add /pub/gpg_key
echo "deb file:///pub wheezy PKGS" > /etc/apt/sources.list.d/local.list

apt-key list
apt-get update
apt-get -y install --no-install-recommends migasfree-client
apt-get -y install --no-install-recommends migasfree-server

cat > /etc/migasfree.conf <<EOF
[client]
Version=CI-TEST

[packager]
User=packager
Password=packager
Version=CI-TEST
Store=org
EOF

DJANGO_SETTINGS_MODULE=migasfree.settings.production python /integration_test.py
