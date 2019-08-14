import unibridge_base
import json
import datetime

# indicator_pendants:
#   module: isy
#   class: indicator
#   trigger: light.hue_pendants
#   trigger_namespace: sway_hassio
#   on_value: 'on'
#   off_value: '??'

#   indicator_topic: insteon/kp/entry/state/5
#   indicator_broker: sway_hassio
#   
class mqtt_switch(base.AppHass):
  def initialize(self):
    self.debug("Initializing trigger {} and indicator {}", self.args["trigger"], self.args["indicator_topic"])
    if isinstance(self.args["on_value"], str):
      self.on_value = [self.args["on_value"]]
    elif isinstance(self.args["on_value"], list):
      self.on_value = self.args["on_value"]
    else:
      self.warn("On value is invalid {}", self.args["on_value"])
      return
#    if isinstance(self.args["indicator"], str):
#      self.indicator = [self.args["indicator"]]
#    elif isinstance(self.args["indicator"], list):
    try:
      self.indicator_topic = self.args["indicator_topic"]
    except:
      self.warn("Indicator is invalid {}", self.args["indicator_topic"])
      return

    self.set_namespace(self.args["trigger_namespace"])
    try:
      self.trigger = self.listen_state(self._trigger,
        self.args["trigger"], duration=60, immediate=True,
        namespace=self.args["trigger_namespace"])
    except:
      self.warn("Listener for trigger {} failed", self.args["trigger"])
      return

  def terminate(self):
    try:
      if self.trigger:
        self.cancel_listen_state(self.trigger)
    except:
      pass
#    self.cancel_listen_state(self.indicator)
#    self.cancel_timer(self.timer)

  def _trigger(self, entity, attribute, old, new, kwargs):
    self.debug("Trigger changed to {}", new)
    if new in self.on_value:
      self.publish(True)
    else:
      self.publish(False)

  def publish(self, is_on):
    topic = self.indicator
    if is_on:
      payload = 'ON'
    else:
      payload = 'OFF'
      
#    self.debug("~~~~~~~~ Publishing entity {} to {} with {}", entity,topic,self.payload)
    self.call_service("mqtt/publish", topic=topic, payload=payload, namespace=self.args["indicator_broker"])

# indicator_pendants:
#   module: indicator
#   class: i2mqtt_scene
#   trigger: light.hue_pendants
#   trigger_namespace: sway_hassio
#   on_value: 'on'
#   off_value: '??'

#   i2mqtt_group: 18
#   i2mqtt_broker: sway_hassio

class i2mqtt_group(base.AppHass):
  def initialize(self):
    self.topic = "insteon/scene/modem"
    self.debug("Initializing trigger {} and indicator {}", self.args["trigger"], self.args["i2mqtt_group"])
    if isinstance(self.args["on_value"], str):
      self.on_value = [self.args["on_value"]]
    elif isinstance(self.args["on_value"], list):
      self.on_value = self.args["on_value"]
    else:
      self.warn("On value is invalid {}", self.args["on_value"])
      return
    try:
      self.i2mqtt_group = int(self.args["i2mqtt_group"])
    except:
      self.warn("Indicator is invalid {}", self.args["i2mqtt_group"])
      return

    self.set_namespace(self.args["trigger_namespace"])
    try:
      self.trigger = self.listen_state(self._trigger,
        self.args["trigger"], duration=60, immediate=True,
        namespace=self.args["trigger_namespace"])
    except:
      self.warn("Listener for trigger {} failed", self.args["trigger"])
      return

  def terminate(self):
    self.cancel_listen_state(self.trigger)

  def _trigger(self, entity, attribute, old, new, kwargs):
    self.debug("Trigger changed to {}", new)
    if new in self.on_value:
      self.publish(True)
    else:
      self.publish(False)

  def publish(self, is_on):
    topic = self.topic
    payload_ht = {}
    payload_ht['group']=self.i2mqtt_group
    if is_on:
      payload_ht['cmd']='on'
    else:
      payload_ht['cmd']='off'
    payload = json.dumps(payload_ht)
#    payload_on: '{ "cmd" : "on", "group" : 18 }'
#    payload_off: '{ "cmd" : "off", "group" : 18 }'
#    self.debug("~~~~~~~~ Publishing entity {} to {} with {}", entity,topic,self.payload)
    self.call_service("mqtt/publish", topic=topic, payload=payload, namespace=self.args["i2mqtt_broker"])