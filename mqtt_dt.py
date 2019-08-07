#import appdaemon.plugins.mqtt.mqttapi as mqtt
import appdaemon.plugins.hass.hassapi as hass
import json

class MQTT_DT(hass.Hass):
  def _log(self, level, message, *args):
    try:
      if args: self.log(message.format(*args), level=level)
      else: self.log(message, level=level)
    except:
      self.log("Debug Logger Failed {}".format(message))
  def warn(self, message, *args):
    level = "WARN"
    self._log(level, message, *args)
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
    if isinstance(self.args["entity_prefix"], str):
      self.entity_prefix = self.args["entity_prefix"]
    else:
      self.warn("Prefix is invalid {}", self.args["entity_prefix"])
      return

    if isinstance(self.args["mqtt_prefix"], str):
      self.mqtt_prefix = self.args["mqtt_prefix"]
    else:
      self.mqtt_prefix = 'device'

    home = self.get_state("zone.home", attribute="all", namespace=self.args["tracker_namespace"])
    self.payload = {}
    self.payload['latitude'] = home['attributes']['latitude']
    self.payload['longitude'] = home['attributes']['longitude']
    try:
      self.payload['gps_accuracy'] = self.args['gps_accuracy']
    except:
      self.payload['gps_accuracy'] = home['attributes']['radius']

    self.trackers = {}
    for entity_id in self.get_state("group.all_devices", attribute="entity_id", namespace=self.args["tracker_namespace"]):
      if entity_id.split('.')[1].startswith(self.prefix):
        name=entity_id.split('.'+self.prefix)[1]
        user=name.split('_')[0]
        device=name.split('_')[1]
        self.trackers[entity_id] = {'name':name, 'user':user, 'device':device}

    try:
      self.trigger = self.listen_state(self._trigger,
        [*self.trackers], new='home', duration=60, immediate=True,
        namespace=self.args["tracker_namespace"])
    except:
      self.warn("Listener for trigger {} failed", [*self.trackers])
      return

  def _trigger(self, entity, attribute, old, new, kwargs):
    topic = self.mqtt_prefix+'/'+trackers[entity]['user']+'/'+trackers[entity]['device']
    self.call_service("mqtt/publish", topic=topic, payload=self.payload)
