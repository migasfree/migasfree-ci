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


if not get_python_lib() in sys.path:
    sys.path.append(get_python_lib())

from migasfree_client.utils import (
    get_config,
    get_hardware_uuid,
    get_mfc_computer_name,
)

from migasfree_client.network import get_first_mac

from migasfree_client import settings as client_settings


class TokenApi(unittest.TestCase):

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

    def info_stack(self, message):
        template = """

        ********************************************************************
        *  %(message)s
        ********************************************************************

        """
        return template % {"message": message}

    def request(self, method, model, data):
        data = json.dumps(data)
        self.connection.request(
            method,
            '/api/v1/token/%s/' % model,
            data,
            self.headers
        )
        response = self.connection.getresponse()
        status = response.status
        body = response.read()
        return (status, body)

    def check_status_ok(self, status, body):
        self.assertTrue(
            status == httplib.OK,
            self.info_stack("Status %s != %s (OK). Body: %s" % (
                status, httplib.OK,
                body
                )
            )
        )

    def check_status_created(self, status, body):
        self.assertTrue(
            status == httplib.CREATED,
            self.info_stack("Status %s != %s (CREATED). Body: %s" % (
                status, httplib.CREATED,
                body
                )
            )
        )

    def check_in(self, value1, value2):
        self.assertTrue(
            value1 in value2,
            self.info_stack("%s is not in %s" % (value1, value2))
        )

    def check_equal(self, value1, value2):
        self.assertEqual(
            value1,
            value2,
            self.info_stack("%s != %s" % (value1, value2))
        )

    def check_field_in(self, body, field, value1):
        value2 = json.loads(body)["results"][0][field]
        self.assertTrue(
            value1 in value2,
            self.info_stack("%s is not in %s" % (value1, value2))
        )

    def check_field_equal(self, body, field, value1):
        value2 = json.loads(body)["results"][0][field]
        self.assertEqual(
            value1,
            value2,
            self.info_stack("%s != %s" % (value1, value2))
        )


class _10_Integrity(TokenApi):
    """
    Test Autoregister computer
    """

    def test_010_migasfree_update(self):
        cmd = "migasfree -u"
        self.check_equal(os.system(cmd), 0)

    def test_020_migasfree_upload(self):
        cmd = """
wget -O - http://migasfree.org/pub/gpg_key | apt-key add -
echo "deb http://migasfree.org/pub wheezy PKGS" > /etc/apt/sources.list.d/migasfree.list
apt-get update
apt-get download migasfree-launcher
_LAUNCHER=$(ls migasfree-launcher*.deb)
migasfree-upload -f "$_LAUNCHER"
rm $_LAUNCHER
"""
        self.check_equal(os.system(cmd), 0)

    def test_030_create_repository(self):
        data = {
            "name": 'test',
            "version": 1,
            "date": str(datetime.datetime.now().date()),
            "toinstall": 'migasfree-launcher',
            "packages": [1],
            "attributes": [1],
        }
        status, body = self.request('POST', 'repositories', data)
        self.check_status_created(status, body)

    def test_040_mandatory_install(self):
        cmd = """
           apt-get --assume-yes purge migasfree-launcher
           migasfree -u
           dpkg -l|grep migasfree-launcher
           """
        self.check_equal(os.system(cmd), 0)

    def test_900_migasfree_label(self):
        config = get_config(client_settings.CONF_FILE, 'client')
        self.uuid = get_hardware_uuid()
        self.url = 'http://%s/computer_label/?uuid=%s&name=%s' % (
            config.get('server', 'localhost'),
            self.uuid,
            get_mfc_computer_name()
        )
        self.label = urllib2.urlopen(self.url).read()
        self.check_in(self.uuid, self.label)


class _20_Unit(TokenApi):
    """
    Test migasfree Token API
    """

    def test_change_status(self):
        data = {"status": "reserved"}
        status, body = self.request('POST', 'computers/1/status', data)
        self.check_status_ok(status, body)

    def test_cid(self):
        data = {
            "name": get_mfc_computer_name(),
            "mac_address": get_first_mac()
        }
        data = urllib.urlencode(data)
        status, body = self.request('GET', 'computers', data)
        self.check_status_ok(status, body)
        self.check_field_equal(body, "name", get_mfc_computer_name())
        self.check_field_equal(body, "uuid", get_hardware_uuid())

    def test_check_package(self):
        status, body = self.request('GET', 'packages', {"id": 1})
        self.check_status_ok(status, body)
        self.check_field_in(body, "name", "migasfree-launcher")


if __name__ == '__main__':
    unittest.main()
