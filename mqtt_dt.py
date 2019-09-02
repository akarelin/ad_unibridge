#import appdaemon.plugins.mqtt.mqttapi as mqtt
import appdaemon.plugins.hass.hassapi as hass
import json
import datetime

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

    try:
      self.mqtt_prefix = self.args["mqtt_prefix"]
    except:
      self.mqtt_prefix = 'device'

    home = self.get_state("zone.home", attribute="all", namespace=self.args["tracker_namespace"])
    payload = {}
    payload['latitude'] = home['attributes']['latitude']
    payload['longitude'] = home['attributes']['longitude']
    try:
      payload['gps_accuracy'] = self.args['gps_accuracy']
    except:
      payload['gps_accuracy'] = home['attributes']['radius']
    self.payload = json.dumps(payload)

    self.trackers = {}
    for entity_id in self.get_state("group.all_devices", attribute="entity_id", namespace=self.args["tracker_namespace"]):
      if entity_id.split('.')[1].startswith(self.entity_prefix):
        name=entity_id.split('.'+self.entity_prefix)[1]
        user=name.split('_')[0]
        device=name.split('_')[1]
        self.trackers[entity_id] = {'name':name, 'user':user, 'device':device}

    try:
      self.trigger = self.listen_state(self._trigger,
        new='home', duration=60, immediate=True,
        namespace=self.args["tracker_namespace"])
    except:
      self.warn("Listener for trigger {} failed", [*self.trackers])
      return
    
    runtime = datetime.time(0, 0, 0)
    self.timer = self.run_minutely(self._timer, runtime)

  def terminate(self):
    self.cancel_listen_state(self.trigger)
    self.cancel_timer(self.timer)

  def _timer(self, kwargs):
    for e in [*self.trackers]:
      state = self.get_state(e, namespace=self.args["tracker_namespace"])
      self.debug("~~~~~~~ Timer processing entity {} with state {}", e, state)
      if state  == 'home':
        self.publish(e)


  def _trigger(self, entity, attribute, old, new, kwargs):
    if entity in [*self.trackers]:
      self.publish(entity)

  def publish(self, entity):
    topic = self.mqtt_prefix+'/'+self.trackers[entity]['user']+'/'+self.trackers[entity]['device']
    self.debug("~~~~~~~~ Publishing entity {} to {} with {}", entity,topic,self.payload)
    self.call_service("mqtt/publish", topic=topic, payload=self.payload, namespace=self.args["tracker_namespace"])
