#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# export DJANGO_SETTINGS_MODULE='migasfree.settings.production'

import unittest

import sys
import os
import datetime
import httplib
import json
import urllib
import urllib2

from distutils.sysconfig import get_python_lib

import django
django.setup()
from django.conf import settings

if not get_python_lib() in sys.path:
    sys.path.append(get_python_lib())

from migasfree_client.utils import (
    get_config,
    get_hardware_uuid,
    get_mfc_computer_name,
    get_mfc_version
)

from migasfree_client import settings as client_settings

import migasfree
from migasfree.server.models import Version, Repository, Package, Computer
from migasfree.server.tasks import create_physical_repository


class _10_AutoRegister(unittest.TestCase):
    """
    Test Autoregister computer
    """

    def setUp(self):
        cmd = "migasfree -u"
        self._return = os.system(cmd)

    def test_check_computer(self):
        self.assertEqual(
            self._return, 0,
            "migasfree -u return error: %s " % self._return
        )
        self.assertEqual(
            Computer.objects.all().count(), 1,
            "Computers count is not 1"
        )


class _20_MigasfreeUpload(unittest.TestCase):
    """
    Test migasfree-upload -f
    """

    def setUp(self):
        migas_version = get_mfc_version()
        cmd = """
wget -O - http://migasfree.org/pub/gpg_key | apt-key add -
echo "deb http://migasfree.org/pub wheezy PKGS" > /etc/apt/sources.list.d/migasfree.list
apt-get update
apt-get download migasfree-launcher
_LAUNCHER=$(ls migasfree-launcher*.deb)
sed -i "s/#User     =/User=packager/g" /etc/migasfree.conf
sed -i "s/#Password =/Password=packager/g" /etc/migasfree.conf
sed -i "s/#Version  =/Version=%s/g" /etc/migasfree.conf
sed -i "s/#Store    =/Store=org/g" /etc/migasfree.conf
migasfree-upload -f "$_LAUNCHER"
rm "$_LAUNCHER"
"""
        os.system(cmd % migas_version)

        cmd = """
sed -i "s/#User     =/User=packager/g" /etc/migasfree.conf
sed -i "s/#Password =/Password=packager/g" /etc/migasfree.conf
sed -i "s/#Version  =/Version=%s/g" /etc/migasfree.conf
sed -i "s/#Store    =/Store=org/g" /etc/migasfree.conf
migasfree-upload -f /ci/dists/*/PKGS/migasfree-launcher_*_all.deb
"""
        os.system(cmd % migas_version)

    def test_upload_file(self):
        pkg = Package.objects.get(pk=1)
        pkg_file = os.path.join(
            settings.MIGASFREE_REPO_DIR,
            pkg.version.name,
            'STORES',
            pkg.store.name,
            pkg.name
        )

        self.assertTrue(
            os.path.exists(pkg_file),
            "Not exists package %s" % pkg_file
        )


class _30_CreateRepository(unittest.TestCase):
    """
    Test Create Repository with mandatory package
    """

    def setUp(self):
        r = Repository()
        r.name = 'test'
        r.version = Version.objects.get(pk=1)
        r.date = datetime.datetime.now()
        r.toinstall = 'migasfree-launcher'
        r.toremove = ''
        r.save()
        r.packages.add(1)
        r.attributes.add(1)
        r.save()
        if len(migasfree.__version__) == 4 or migasfree.__version__ >= "4.2":
            create_physical_repository({}, r, [1])
        else:
            create_physical_repository(r, [1])
        self.repo = r

        # Cambiamos propietario porque lo hemos creado como root
        os.system(
            "_USER=$(ls -la %(repo)s | grep %(version)s | cut -d ' ' -f 3); chown -R $_USER %(repo)s" % {
                "repo": settings.MIGASFREE_REPO_DIR,
                "version": r.version.name
            }
        )

    def test_exist_pkg(self):
        pkg_file = os.path.join(
            settings.MIGASFREE_REPO_DIR,
            self.repo.version.name,
            self.repo.version.pms.slug,
            self.repo.name,
            'PKGS',
            self.repo.packages.all()[0].name
        )

        self.assertTrue(
            os.path.exists(pkg_file),
            "Not exists file: %s" % pkg_file
        )


class _40_MigasfreeInstallMandatory(unittest.TestCase):
    """
    Test migasfree -u (install mandatory package)
    """

    def setUp(self):
        cmd = """
           apt-get --assume-yes purge migasfree-launcher
           migasfree -u
           dpkg -l|grep migasfree-launcher
           """
        self._return = os.system(cmd)

    def test_update(self):
        """
        Test migasfree-update
        """
        self.assertEqual(
            self._return, 0,
            "migasfree-launcher is not installed!"
        )


class _90_MigasfreeLabel(unittest.TestCase):
    """
    Test migasfree-label
    """

    def setUp(self):
        config = get_config(client_settings.CONF_FILE, 'client')

        self.uuid = get_hardware_uuid()
        self.url = 'http://%s/computer_label/?uuid=%s&name=%s' % (
            config.get('server', 'localhost'),
            self.uuid,
            get_mfc_computer_name()
        )

        self.label = urllib2.urlopen(self.url).read()

    def test_label(self):
        self.assertTrue(
            self.uuid in self.label,
            "Not Found %s in url %s" % (self.uuid, self.url)
        )


class _50_MigasfreeTokenApi(unittest.TestCase):
    """
    Test migasfree Token API
    """

    def setUp(self):
        config = get_config(client_settings.CONF_FILE, 'client')
        host = config.get('server', 'localhost')
        data = json.dumps({"username": "admin", "password": "admin"})
        self.connection = httplib.HTTPConnection(host)
        headers = {"Content-type": "application/json"}
        self.connection.request('POST', '/token-auth/', data, headers)

        response = self.connection.getresponse()
        status = response.status
        body = response.read()
        self.assertTrue(
            status == httplib.OK,
            "Status: %s\nInfo: %s" % (status, body)
        )
        self.token = json.loads(body)["token"]
        self.headers = {
            "Content-type": "application/json",
            "Authorization": "Token %s" % self.token
        }

    def test_change_status(self):
        data = json.dumps({"status": "reserved"})
        url = '/api/v1/token/computers/1/status/'
        self.connection.request(
            'POST',
            url,
            data,
            self.headers
        )

        response = self.connection.getresponse()
        status = response.status
        body = response.read()
        self.assertTrue(
            status == httplib.OK,
            "Status: %s\nInfo: %s" % (status, body)
        )

        c = Computer.objects.get(pk=1)
        self.assertTrue(
            c.status == 'reserved',
            "Incorrect Computer Status: %s" % c.status
        )

    def test_cid(self):
        c = Computer.objects.get(pk=1)

        data = {
            "name": c.name,
            "mac_address": c.mac_address[0:11]
        }
        data = urllib.urlencode(data)

        url = '/api/v1/token/computers/'
        self.connection.request(
            'GET',
            url,
            data,
            self.headers
        )

        response = self.connection.getresponse()
        status = response.status
        body = response.read()
        self.assertTrue(
            status == httplib.OK,
            "Status: %s\nInfo: %s" % (status, body)
        )

        self.assertTrue(
            c.id == json.loads(body)['results'][0]['id'],
            "Incorrect Computer ID: %s" % json.loads(body)['results'][0]['id']
        )


if __name__ == '__main__':
    unittest.main()
