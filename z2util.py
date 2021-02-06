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
  z2base_topic = None
  bridge_base_topic = None
  util_base_topic = None
  disco_topics = []

# region construc/destruct
  def initialize(self):
    super().initialize()
  
    self.z2_base_topic = self.args.get('z2_base_topic')
    self.bridge_base_topic = self.args.get('bridge_base_topic')
    self.util_base_topic = self.args.get('util_base_topic')
    self.disco_topics = self.args.get('disco_topics')

    self.mqtt.mqtt_unsubscribe(self.bridge_base_topic+'/#')
    self.mqtt.mqtt_unsubscribe(self.util_base_topic+'/#')
    self.mqtt.listen_event(self.c_mqtt_bridge, "MQTT_MESSAGE", wildcard = self.bridge_base_topic+'/#')
    self.mqtt.listen_event(self.c_mqtt_util, "MQTT_MESSAGE", wildcard = self.util_base_topic+'/#')
    self.api.sleep(60)
    self.mqtt.mqtt_subscribe(self.bridge_base_topic+'/#')
    self.mqtt.mqtt_subscribe(self.util_base_topic+'/#')
  
  def terminate(self):
    self.mqtt.mqtt_unsubscribe(self.bridge_base_topic+'/#')
    self.mqtt.mqtt_unsubscribe(self.util_base_topic+'/#')
#    super.terminate()
# endregion

# region MQTT event callbacks
  def c_mqtt_bridge(self, event_name, data, kwargs):
    topic = data.get('topic').split(self.bridge_base_topic)[1]
    payload = data.get('payload')
    if topic == '/state':
      self.state = payload
    elif topic == '/devices':
      self.devices = json.loads(payload)
    elif topic == '/groups':
      self.groups = json.loads(payload)

  def c_mqtt_util(self, event_name, data, kwargs):
    topic = data.get('topic').split(self.util_base_topic)[1]
    payload = data.get('payload')
    if topic == '/poll':
      self.poll()
      self.publish_state()
    elif topic == '/get':
      self.publish_state()
    elif topic == '/discover/groups/do':
      self.publish_disco4groups()
    elif topic == '/discover/groups/undo':
      self.publish_disco4groups(unpublish = True)
    elif topic == '/poweron':
      self.publish_poweron()
# endregion

  def poll(self):
    self.debug("Polling")
    for d in self.devices:
      name = d.get('friendly_name')
      self.debug("Name: {}", name)
      topic = self.bridge_base_topic + "/" + name + "/get"
      self.mqtt.mqtt_publish(topic, '{"state": ""}')
      self.api.sleep(30)

  def publish_poweron(self):
    self.debug("Publishing poweron")
    for d in self.devices:
      name = None
      features = []
      name = d.get('friendly_name')
      if not name:
        self.warn("Unrecognized device {}", d)
        continue

      c = {}
      topic = self.bridge_base_topic + "/" + name + "/set"

      definition = d.get('definition')
      if not definition:
        self.warn("Device {} is not defined", d)
        continue

      exposes = definition.get('exposes')
      if not exposes[0]:
        self.warn("Device {} does not expose any methods", d)
        continue
      
      features = exposes[0]
      for f in features:
        f_name = f.get('name')
        if f_name == 'state':
          c['hue_power_on_behavior'] = "on"
        elif f_name == 'brightness':
          c['hue_power_on_brightness'] = 2
        elif f_name == 'color_temp':
          c['hue_power_on_color_temperature'] = 500
        elif f_name == 'color_xy':
          c['hue_power_on_color'] = "#0000FF"
      self.mqtt.mqtt_publish(topic, c)
      self.api.sleep(30)

  def publish_state(self):
    self.debug("Publishing state")
    s = f"\nBridge State: {self.state}"
    s += f"\n\tDevices: {len(self.devices)}"
    s += f"\n\tGroups: {len(self.groups)}"
    self.mqtt.mqtt_publish(self.util_base_topic+"/state", s)

# region Discovery
  def publish_disco4groups(self, unpublish = False):
    self.debug("Publishing group discovery")
    availability_topic = f"{self.bridge_base_topic}/state"
    for g in self.groups:
      g_name = g.get('friendly_name')
      g_id = g.get('id')
      unique_id = f'z2_g_{g_id}'

      for dt in self.disco_topics:
        config_topic = f"{dt}/g_{g_id}/config"
      
        if unpublish:
          self.mqtt.mqtt_publish(config_topic)
        else:
          p = {}
          main_topic = f"{self.z2_base_topic}/{g_name}"
          p['~'] = config_topic
          p['name'] = g_name
          p['unique_id'] = unique_id
          p['cmd_t'] = f"{main_topic}/set"
          p['stat_t'] = main_topic
          p['schema'] = 'json'
          p['brightness'] = True
          p['brightness_scale'] = 254
          p['color_temp'] = True
          p['xy'] = True
          p['rgb'] = True
          p['availability_topic'] = availability_topic
          self.mqtt.mqtt_publish(config_topic, json.dumps(p))
# endregion

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

