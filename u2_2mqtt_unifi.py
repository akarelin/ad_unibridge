"""
Support for Unifi WAP controllers.
"""
import logging
import datetime
import time
from datetime import timedelta
import os
from threading import Thread
import json
import paho.mqtt.client as mqtt
from pyunifi.controller import unifi

#DEFAULT_HOST = 'localhost'
UNIFI_PORT = 8443
UNIFI_SITE = 'default'
UNIFI_VERIFY_SSL = False
UNIFI_REFRESH_TIME = 15
UNIFI_DETECTION_TIME = 180

class Unifi2MQTT(u3.U3):
  detection_time = 0
  controller = None
  scanner = None
  clients = []
  all_clients = []
  def initialize(self):
    super().initialize()
    host = self.args.get('unifi_host')
    user = self.args.get('unifi_user')
    password = self.args.get('password')
    port = self.args.get('port', UNIFI_PORT)
    site_id = self.args.get('site_id', UNIFI_SITE)

    try:
      self.controller = Controller(host, user, password, port, version='v4', site_id=site_id, ssl_verify=UNIFI_VERIFY_SSL)
      self.detection_time = int(self.args.get('detection_time',UNIFI_DETECTION_TIME))
      self.scanner = UnifiScanner(unifi, timedelta(seconds=detection_time))
    except:
      self.Error(f"Unable to initialize controller with {host}, {user}, {passwrd}, {port}, {site_id}")
      raise Exception(AssertionError())
    self.refresh()
  
  def load_clients(self):
    from pyunifi.controller import APIError
    try:
      clients = self.controller.get_clients()
    except APIError as ex:
      self.Error(f"Failed to scan clients: {ex}")
      clients = []

    self.all_clients = {
      client['mac']: client
      for client in clients
    }

    self.clients = {
      client['mac']: client
      for client in clients
      if (datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(float(client['last_seen']))) < self.detection_time
    }

  def refresh_clients(self):
    new_clients = set(self.scan_devices())

    # Disappeared
    gone = self._present - new_devices
    appeared = new_devices - self._present

    self._present = new_devices

        return gone, appeared

    def scan_devices(self):
        """Scan for devices."""
        self._update()
        return self._clients.keys()

    def get_device_name(self, mac):
        """Return the name (if known) of the device.

        If a name has been set in Unifi, then return that, else
        return the hostname if it has been detected.
        """
        client = self._all_clients.get(mac, {})
        name = client.get('name') or client.get('hostname')
        _LOGGER.debug("Device mac %s name %s", mac, name)
        return name

def refresh_loop(client):
    scanner = get_scanner()

    while True:
        gone, appeared = scanner.get_diff()

        out = []
        for mac in gone:
            data = { 'type': 'disappear', 'mac': mac, 'hostname': scanner.get_device_name(mac) }
            out.append(data)

        for mac in appeared:
            data = { 'type': 'appear', 'mac': mac, 'hostname': scanner.get_device_name(mac) }
            out.append(data)

        for data in out:
            msg = json.dumps(data)
            print msg
            client.publish(os.environ['MQTT_TOPIC'], msg)

        time.sleep(DEFAULT_REFRESH_TIME)

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT with result code "+str(rc))

client = mqtt.Client()
client.on_connect = on_connect

if os.environ.get('MQTT_PORT', None) is None:
    port = 1883
else:
    port = int(os.environ['MQTT_PORT'])

client.connect(os.environ['MQTT_BROKER'], port, 60)

t = Thread(target=refresh_loop, args=(client,))
t.start()

client.loop_forever()