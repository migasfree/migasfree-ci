#!/usr/bin/env python
# -*- coding: UTF-8 -*-

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
    get_mfc_version
)

from migasfree_client.network import get_first_mac

from migasfree_client import settings as client_settings


class TokenApi(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        self.user = "admin"
        self.password = "admin"
        super(TokenApi,self).__init__(*args, **kwargs)

    def setUp(self):
        config = get_config(client_settings.CONF_FILE, 'client')
        host = config.get('server', 'localhost')
        data = json.dumps({"username": self.user, "password": self.password})
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

    def request(self, method, model, data={}, params={}):
        data = json.dumps(data)
        if params:
            params = '?' + urllib.urlencode(params)
        else:
            params = ''
        self.connection.request(
            method,
            '/api/v1/token/%s/%s' % (model, params),
            data,
            self.headers
        )
        response = self.connection.getresponse()
        self.status = response.status
        self.body = response.read()

    def check_status_ok(self):
        self.assertTrue(
            self.status == httplib.OK,
            self.info_stack("Status %s != %s (OK). Body: %s" % (
                self.status, httplib.OK,
                self.body
                )
            )
        )

    def check_status_created(self):
        self.assertTrue(
            self.status == httplib.CREATED,
            self.info_stack("Status %s != %s (CREATED). Body: %s" % (
                self.status, httplib.CREATED,
                self.body
                )
            )
        )

    def check_status_forbidden(self):
        self.assertTrue(
            self.status == httplib.FORBIDDEN,
            self.info_stack("Status %s != %s (FORBIDDEN). Body: %s" % (
                self.status, httplib.FORBIDDEN,
                self.body
                )
            )
        )

    def check_true(self, value1):
        self.assertTrue(
            value1,
            self.info_stack("Not True")
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

    def check_field_in(self, field, value1):
        value2 = json.loads(self.body)[field]
        self.assertTrue(
            value1 in value2,
            self.info_stack("%s is not in %s" % (value1, value2))
        )

    def check_field_equal(self, field, value1):
        value2 = json.loads(self.body)[field]
        self.assertEqual(
            value1,
            value2,
            self.info_stack("%s != %s" % (value1, value2))
        )

    def count(self):
        return  json.loads(self.body)["count"]


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
            "toremove": '',
            "packages": [1],
            "attributes": [1],
        }
        self.request('POST', 'repositories', data)
        self.check_status_created()

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


class _20_check_integrity_data(TokenApi):

    def test_010_check_platform(self):
        self.request('GET', 'platforms/%s/' % 1)
        self.check_status_ok()
        self.check_field_equal("name", "Linux")

    def test_020_check_version(self):
        self.request('GET', 'versions/%s/' % 1)
        self.check_status_ok()
        self.check_field_equal("name", get_mfc_version())

    def test_030_computer(self):
        params = {
            "name": get_mfc_computer_name(),
            "mac_address": get_first_mac()
        }
        self.request('GET', 'computers', {}, params)
        self.check_status_ok()
        self.check_true(self.count() == 1)
        id=json.loads(self.body)["results"][0]["id"]
        
        self.request('GET', 'computers/%s/' % id)
        self.check_status_ok()
        self.check_field_equal("name", get_mfc_computer_name())
        self.check_field_equal("uuid", get_hardware_uuid())
        self.check_field_equal("mac_address", get_first_mac())

    def test_040_check_migration(self):
        self.request('GET', 'migrations/%s/' % 1)
        self.check_status_ok()
        self.check_field_equal("computer",
            {"id": 1, "cid_description": get_mfc_computer_name()}
        )

    # TODO updates
    # TODO Login

    def test_060_check_attribute(self):
        self.request('GET', 'attributes')
        self.check_status_ok()
        self.check_true(self.count() > 1)

    def test_080_check_user(self):
        self.request('GET', 'users/%s/' % 1)
        self.check_status_ok()
        self.check_field_equal("name", "root")

    def test_100_check_store(self):
        self.request('GET', 'stores/%s/' % 1)
        self.check_status_ok()
        self.check_field_equal("name", "org")

    def test_110_check_package(self):
        self.request('GET', 'packages/%s/' % 1)
        self.check_status_ok()
        self.check_field_in("name", "migasfree-launcher")

    def test_110_check_repository(self):
        self.request('GET', 'repositories/%s/' % 1)
        self.check_status_ok()
        self.check_field_equal("name", "test")
        self.check_field_equal("version", {"id": 1, "name": get_mfc_version()})


class _30_Unit(TokenApi):
    """
    Test migasfree Token API
    """

    def test_010_change_status(self):

        # Change status to reserved
        data = {"status": "reserved"}
        self.request('POST', 'computers/%s/status/' % 1, data)
        self.check_status_ok()

        self.request('GET', 'computers/%s/' % 1)
        self.check_status_ok()
        self.check_field_equal("status", "reserved")


class _40_Permissions(TokenApi):
    """
    Test migasfree Token API
    """

    def __init__(self, *args, **kwargs):
        self.user = "reader"
        self.password = "reader"
        super(TokenApi,self).__init__(*args, **kwargs)

    def test_010_change_status_forbidden(self):

        # Change status to reserved
        data = {"status": "intended"}
        self.request('POST', 'computers/%s/status/' % 1, data)
        self.check_status_forbidden()
        # Check status is not changed
        self.request('GET', 'computers/%s/' % 1)
        self.check_status_ok()
        self.check_field_equal("status", "reserved")


if __name__ == '__main__':
    unittest.main()
