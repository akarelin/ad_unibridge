import unibridge

# region Constants
OFF = 'OFF'
ON = 'ON'
# endregion

# region MqttDevice
class MqttDevice(MqttApp):
  unique_id = None
  state = OFF
  brightness = None
  friendly_name = None

  topic_base = None
  topic_cmd_switch = None
  topic_cmd_brightness = None
  topic_state = None
  disco_topics = []
  
  def initialize(self):
    super().initialize()

    self.topic_base = self.args.get('topic')
    self.topic_cmd_switch = '/'.join([self.topic_base, "switch"])
    self.topic_state = '/'.join([self.topic_base, "state"])

    disco = self.args.get('disco')
    if disco:
      if not isinstance(disco, list):
        self.disco_topics = [disco]
      else:
        self.disco_topics = disco
    self.unique_id = '_'.join(self.topic_base)
    self.friendly_name = self.args.get('friendly_name')

    self.mqtt.mqtt_unsubscribe(self.topic_cmd_switch)
    self.mqtt.listen_event(self.c_mqtt_cmd_switch, "MQTT_MESSAGE", topic = self.topic_cmd_switch)
    self.mqtt.mqtt_subscribe(self.topic_cmd_switch)
  
  def terminate(self):
    super().terminate()
    self.mqtt.mqtt_unsubscribe(self.topic_cmd_switch)

  def publish_state(self):
    s = {}
    s['state'] = self.state
    if self.state == ON:
      s['brightness'] = self.brightness
    self.mqtt.mqtt_publish(self.topic_state, json.dumps(s))

# region discovery
  def publish_device(self, unpublish = False):
    for dt in self.disco_topics:
      config_topic = f"{dt}/{self.unique_id}/config"
      
      if unpublish:
        self.mqtt.mqtt_publish(config_topic)
      else:
        p = {}
        p['~'] = config_topic
        p['name'] = self.friendly_name
        p['unique_id'] = self.unique_id
        p['cmd_t'] = self.topic_cmd_brightness
        p['stat_t'] = self.state_topic
        p['schema'] = 'json'
        p['brightness'] = True
        p['brightness_scale'] = 254
        self.mqtt.mqtt_publish(config_topic, json.dumps(p))
# endregion

# region callbacks 
  def _callback_switch(self, event_name, data, kwargs):
    payload = data.get('payload')
    if payload == ON:
      self.state = ON
      if not self.brightness: self.brightness = 127
      self.command(ON)
    elif payload == OFF:
      self.state = OFF
      self.command(OFF)
    self.publish_state()
# endregion

  @abstractmethod
  def command(self):
    raise NotImplemented

    # if self.state == ON and self.brightness:
    #   self.set_app_state(self.entity, {"state": self.state, "brightness": self.brightness})
    # else:
    #   self.set_app_state(self.entity, {"state": self.state})

    # entity_id = self.args.get('entity_id')
    # if self.api.entity_exists(entity_id, namespace = "ao"):
    #   self.api.call_service("state/set", entity_id=entity_id, state=self.state.lower(), brightness = self.brightness, namespace = 'ao')
    # else:
    #   self.api.call_service("state/add_entity", entity_id=entity_id, state=self.state.lower(), brightness = self.brightness, namespace = 'ao')

  # def turn_on(self, **kwargs):
  #   self.command(ON, kwargs)

  # def turn_off(self, **kwargs):
  #   self.command(OFF, kwargs)

