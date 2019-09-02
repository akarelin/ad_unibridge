import appdaemon.plugins.mqtt.mqttapi as mqtt
import json

class Unifi2DT(mqtt.Mqtt):
  def _log(self, level, message, *args):
    try:
      if args: self.log(message.format(*args), level=level)
      else: self.log(message, level=level)
    except:
      self.log("Debug Logger Failed {}".format(message))
  def warn(self, message, *args):
    level = "WARN"
    self._log(level, const_warn_level, message, *args)
  def debug(self, message, *args):
    level = "INFO"
    enabled = False
    try: 
      if self.args["debug"] == True:
        enabled = True
    except: 
      pass
    if not enabled: 
      return
    self._log(level, message, *args)

  def initialize(self):
    try: self.topic = self.args["topic"]
    except: self.topic = "unifi/+/status/wifi/+/client/+"
    self.set_namespace(self.args['namespace'])

    self.sites = {}
    try: self.sites = self.args["sites"]
    except:
      self.warn("Sites are invalid {}", self.args["sites"])
      return

    self.devices = {}
    try: self.devices = self.args["devices"]
    except:
      self.warn("Devices are invalid {}", self.args["devices"])
      return

 #   self.debug("~~~~ Devices {}", self.devices)
 #   self.debug("~~~~ Sites {}", self.sites)
    self.mqtt_subscribe(self.topic)
    self.mqtt_listener = self.listen_event(self._mqtt_trigger, "MQTT_MESSAGE")
    
  def terminate(self):
    try:
      self.mqtt_unsubscribe(self.topic)
      self.cancel_listen_event(self.mqtt_listener)
    except:
      pass

  def _mqtt_trigger(self, event_name, data, kwargs):
#    self.debug("Topic {} Payload {}", data['topic'], data['payload'])

    try:
      payload = json.loads(data['payload'])
      site = data['topic'].split('/')[1]
      ap = data['topic'].split('/')[4]
      name = data['topic'].split('/')[6]
      val = payload['val']
      mac = payload['mac']
      ts = payload['ts']
    except:
#      self.debug("Not for us")
      return

    if not val:
#      self.debug("~~~~~~ {} Not here", name)
      return
   
    try:
      device = self.devices[mac]
#      self.debug("~~~~~ {} Our Device", device)
    except:
#      self.debug("~~~~~ {} Not our device", mac)
      return

    location = {}
    try:
      location = self.sites[site]
#      self.debug("~~~~~ {} Our location", location)
    except:
#      self.debug("~~~~~ {} Not our site", site)
      return

    topic = 'device/'+device
    payload = json.dumps(location)
    self.debug("~~~~~~~ {} => {}", topic, payload)
    self.mqtt_publish(topic, payload, qos = 0, retain = False, namespace = self.args['namespace'])