#!/bin/bash

apt-key add /pub/gpg_key
echo "deb file:///pub wheezy PKGS" > /etc/apt/sources.list.d/local.list

apt-key list
apt-get update

# añadir dependencia openssl al cliente issue: https://github.com/migasfree/migasfree-client/issues/60
apt-get -y install  openssl

apt-get -y install --no-install-recommends migasfree-client

sed -i "s/# Server =/# Server =$FQDN/g" /etc/migasfree.conf

DJANGO_SETTINGS_MODULE=migasfree.settings.production python /run-test.py
