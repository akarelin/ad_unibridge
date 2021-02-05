import json
import unibridge

"""
z2poll:
  module: mqtt
  class: MqttScript

  base_topic: z2mqtt

"""

class Z2Bridge(unibridge.MqttApp):
  info = {}
  devices = []
  groups = []
  config = {}
  state = None
  base_topic = None

  def initialize(self):
    super().initialize()
  
    self.base_topic = self.args.get('base_topic')
    self.bridge_topic = self.base_topic + "/bridge/#"

    self.mqtt.mqtt_unsubscribe(self.bridge_topic)
    self.mqtt.mqtt_subscribe(self.bridge_topic)
    self.mqtt.listen_event(self._mqtt_callback, "MQTT_MESSAGE", wildcard = self.bridge_topic)
    self.api.run_in(self.poll, 60)

  def poll(self, kwargs):
    self.debug("Polling")
    for d in self.devices:
      name = d.get('friendly_name')
      self.debug("Name: {}", name)
      topic = self.base_topic + "/" + name + "/get"
#      self.debug("Topic: {}", topic)
      self.mqtt.mqtt_publish(topic, '{"state": ""}')
#      self.mqtt.mqtt_publish(topic, '{"hue_power_on_behavior": ""}')
      self.api.sleep(30)
      self.set_poweron(name)

  def set_poweron(self, name):
    topic = self.base_topic + "/" + name + "/set"
    c = {}
    c['hue_power_on_behavior'] = "on"
    c["hue_power_on_brightness"] = 2
    c["hue_power_on_color_temperature"] = 500
#    "hue_power_on_color": "#0000FF",        // color in hex notation, e.g. #0000FF = blue
    self.mqtt.mqtt_publish(topic, c)

  def trigger(self, kwargs):
    self.dumpstate()
    self.poll(kwargs)

  def _mqtt_callback(self, event_name, data, kwargs):
    topic = data.get('topic').split('/bridge/')[1]
    payload = data.get('payload')
#    self.debug("Callback {} {}", topic, payload)

    if topic == 'state':
      self.state = payload
    elif topic == 'devices':
      self.devices = json.loads(payload)
    elif topic == 'groups':
      self.groups = json.loads(payload)

  def dumpstate(self):
    s = f"\nBridge State: {self.state}"
    s += f"\n\tDevices: {len(self.devices)}"
    s += f"\n\tGroups: {len(self.groups)}"
    self.api.log(s)
  
  def available(self):
    if self.devices and self.groups and self.config:
      if self.state in ['online','offline']:
        return self.state
      else:
        return 'unknown'
    else:
      return 'not loaded'


  # def publish(self):
  #   state = {}
  #   state['outputs'] = json.dumps(self.outputs)
  #   state['devices'] = json.dumps(self.devices)
  #   state['inputs'] = json.dumps(self.inputs)
  #   state['HDMI'] = self.outputs['HDMI']
  #   state['HDBT'] = self.outputs['HDBT']

  #   self.mqtt.mqtt_publish("atlona/state", json.dumps(state))
  #   self.mqtt.mqtt_publish("atlona/state/devices", json.dumps(self.devices))
  #   self.mqtt.mqtt_publish("atlona/state/outputs", json.dumps(self.outputs))
  #   self.mqtt.mqtt_publish("atlona/state/output/hdmi", self.outputs['HDMI'])
  #   self.mqtt.mqtt_publish("atlona/state/output/hdbt", self.outputs['HDBT'])
    
  # def trigger(self, kwargs):
  #   self.refresh()

