import u3

def MQTTCompare(subscription: str, topic: str) -> bool():
  sparts = subscription.split('/')
  tparts = topic.split('/')
  for i, s in enumerate(sparts):
    if s == '#': return True
    elif s == '+': continue
    elif tparts[i] == s: continue
    else: return False

class MqttTopic:
  TP_TOPIC = 'topic'
  TP_SINGLE = 'single'
  TP_MULTI = 'multi'

  types = ['topic','single','multi']
  tparts = []
  type = None
  
  def __init__(self, t = None):
    if t:
      self.tparts = t.split('/')
      if len(tpart) <= 1:
        return None
      elif '#' in tparts:
        self.type = TP_MULTI
      elif '+' in tparts:
        self.type = TP_SINGLE
      else: self.type = TP_TOPIC
  def __str__(tparts):
    return self.topic()
  def __add__(self, other):
    return '/'.join(self, other)
  @property
  def topic(self) -> str:
    if tparts: return tparts.join('/')
    else: return None

class MqttDevice(U3):
  unique_id = str
  name = str
  slug = str
  state = Dict
  topic = Dict[MqttTopic, int]

  def initialize(self):
    super().initialize()
    self.topic['base'] = MqttTopic(self.args.get('topic'))
    self.topic['set'] = self.topic['base'] + "set"
    self.topic['state'] = self.topic['base'] + "state"
    disco = self.args.get('disco')
    if disco:
      if not isinstance(disco, list): self.topic['disco'] = [disco]
      else: self.topic['disco'] = disco
    self.mqtt.mqtt_unsubscribe(self.topic['set'])
    self.mqtt.listen_event(self.c_set, "MQTT_MESSAGE", topic = self.topic['set'])
    self.mqtt.mqtt_subscribe(self.topic['set'])
  
  def terminate(self):
    self.mqtt.mqtt_unsubscribe(self.topic['set'])
    super().terminate()

  @abstractmethod(callable)
  def set(self, state, kwargs):
    self.state = state
    self.publish_state()
  def __set(self, state, kwargs):
    self.set(state, kwargs)
  def turn_on(self, kwargs):
    self.set(ON)
  def turn_off(self):
    self.set(OFF)

  def c_set(self, event_name, data, kwargs):
    payload = data.get('payload')
    if payload == ON: self.turn_on(kwargs)
    elif payload == OFF: self.turn_off()
    else: self.Warn(f"Unknown payload {payload}")
  def publish_state(self):
    self.mqtt.mqtt_publish(self.topic['state'], json.dumps(self.state))

  def disco_payload(self, topic) -> Dict:
    p = Dict
    p['~'] = topic
    p['name'] = self.name
    p['unique_id'] = self.unique_id
    p['stat_t'] = self.topic['state']
    return p

  def publish_device(self, unpublish = False):
    for dt in self.topic['disco']:
      topic = MqttTopic(f"{dt}/{self.unique_id}/config")
      self.mqtt.mqtt_publish(topic, self.disco_payload(topic) if not unpublish)

# region Constants
OFF = 'OFF'
ON = 'ON'
# endregion

class MqttSwitch(MqttDevice):
  def initialize(self):
    super().initialize()
    self.unique_id = '_'.join(self.topic['base']+'switch')
    self.name = self.args.get('name')
    self.slug = self.args.get('slug')

class MqttLight(MqttSwitch):
  def initialize(self):
    super().initialize()

  def disco_payload(self, topic) -> Dict:
    p = super().disco_payload(topic)
    p['cmd_t'] = self.topic['state']
    p['brightness'] = True
    p['brightness_scale'] = 254
    p['schema'] = 'json'
    return p

# region MqttDevice
# class MqttDevice(MqttApp):
#   unique_id = None
#   state = OFF
#   brightness = None
#   friendly_name = None

#   topic_base = None
#   topic_cmd_switch = None
#   topic_cmd_brightness = None
#   topic_state = None
#   disco_topics = []
  
#   def initialize(self):
#     super().initialize()

#     self.topic_base = self.args.get('topic')
#     self.topic_cmd_switch = '/'.join([self.topic_base, "switch"])
#     self.topic_state = '/'.join([self.topic_base, "state"])

#     disco = self.args.get('disco')
#     if disco:
#       if not isinstance(disco, list):
#         self.disco_topics = [disco]
#       else:
#         self.disco_topics = disco
#     self.unique_id = '_'.join(self.topic_base)
#     self.friendly_name = self.args.get('friendly_name')

#     self.mqtt.mqtt_unsubscribe(self.topic_cmd_switch)
#     self.mqtt.listen_event(self.c_mqtt_cmd_switch, "MQTT_MESSAGE", topic = self.topic_cmd_switch)
#     self.mqtt.mqtt_subscribe(self.topic_cmd_switch)
  
#   def terminate(self):
#     super().terminate()
#     self.mqtt.mqtt_unsubscribe(self.topic_cmd_switch)

#   def publish_state(self):
#     s = {}
#     s['state'] = self.state
#     if self.state == ON:
#       s['brightness'] = self.brightness
#     self.mqtt.mqtt_publish(self.topic_state, json.dumps(s))

# # region discovery
#   def publish_device(self, unpublish = False):
#     for dt in self.disco_topics:
#       config_topic = f"{dt}/{self.unique_id}/config"
      
#       if unpublish:
#         self.mqtt.mqtt_publish(config_topic)
#       else:
#         p = {}
#         p['~'] = config_topic
#         p['name'] = self.friendly_name
#         p['unique_id'] = self.unique_id
#         p['cmd_t'] = self.topic_cmd_brightness
#         p['stat_t'] = self.state_topic
#         p['schema'] = 'json'
#         p['brightness'] = True
#         p['brightness_scale'] = 254
#         self.mqtt.mqtt_publish(config_topic, json.dumps(p))
# # endregion

# # region callbacks 
#   def _callback_switch(self, event_name, data, kwargs):
#     payload = data.get('payload')
#     if payload == ON:
#       self.state = ON
#       if not self.brightness: self.brightness = 127
#       self.command(ON)
#     elif payload == OFF:
#       self.state = OFF
#       self.command(OFF)
#     self.publish_state()
# # endregion

#   @abstractmethod
#   def command(self):
#     raise NotImplemented

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


# region JUNK
"""
class MqttApp(AppBase):
  triggers = []
  
  def initialize(self):
    super().initialize()
    self.mqtt = self.get_plugin_api(self.args.get('mqtt_namespace','mqtt'))
    self.hass = self.get_plugin_api(self.args.get('default_namespace'))
    self.debug("Triggers {}", self.args.get('triggers'))
    self.add_triggers()
  
  def terminate(self):
    for t in self.triggers:
      if t.get('type') == TRIGGER_TIMER:
        return

  def add_triggers(self, triggers = []):
    if not triggers: triggers = self.args.get('triggers')
    if not triggers: return
   
    self.debug("Triggers {}", triggers)
    for t in triggers:
      if t['type'] == TRIGGER_TIMER: self.add_time_trigger(t)
      else:
        self.error("Invalid trigger type {}", t)
        continue

  def add_time_trigger(self, trigger):
    t = {}
    t['type'] = TRIGGER_TIMER
    interval = trigger.get('interval')
    if not interval:
      self.error("Unknown trigger {}", trigger)
      return
    t['interval'] = interval
    start = trigger.get('start',"now")
    t['start'] = start
    t['handle'] = self.api.run_every(self.trigger, start, interval)
    self.triggers.append(t)

  @abstractmethod
  def trigger(self, payload):
    raise NotImplementedError
endregion

region App
class App(AppBase):
  triggers = []self.mqtt.listen_event

  def initialize(self):
    super().initialize()
    self.hass = self.get_plugin_api(self.default_namespace)

    self.debug("Namespace {} hass {}", self.default_namespace, self.hass)    

    self.mqtt = self.get_plugin_api(self.default_mqtt_namespace)
    self.add_triggers()

  def terminate(self):
    for t in self.trigger_data:
      if t['type'] == TRIGGER_EVENT:
        self.hass.cancel_listen_event(t['handle'])
      elif t['type'] == TRIGGER_MQTT:
        self.mqtt.cancel_listen_event(t['handle'])

  def add_triggers(self, triggers = []):
    if not triggers: triggers = self.args.get('triggers')
    if not triggers: return
   
    self.debug("Triggers {}", triggers)
    for t in triggers:
      if t['type'] == TRIGGER_MQTT:
        t['event'] = EVENT_MQTT
        self.add_event_trigger(t)
      elif t['type'] == TRIGGER_EVENT: self.add_event_trigger(t)
      elif t['type'] == TRIGGER_STATE: self.add_state_trigger(t)
      else:
        self.error("Invalid trigger type {}",t)
        continue
  
  def add_event_trigger(self, event_data):
    data = event_data
    if 'event' not in data:
      data['event'] = EVENT_MQTT
    self.debug("Adding event trigger {}", event_data)
    trigger = {}
    trigger['event'] = data['event']

    if not data.get('namespace'):
      if data['event'] == EVENT_MQTT: data['namespace'] = self.default_mqtt_namespace
      else: data['namespace'] = self.default_namespace

    if data['event'] == EVENT_MQTT:
      trigger['type'] = TRIGGER_MQTT
      trigger['handle'] = self.mqtt.listen_event(self._event_callback, **data)
    else:
      trigger['type'] = TRIGGER_EVENT
      trigger['handle'] = self.hass.listen_event(self._event_callback, **data)

    if trigger['handle']: self.triggers.append(trigger)
    else: self.error("Trigger no bueno")

  def add_state_trigger_entity(self, entity, state_data):
    data = state_data
    trigger = {}

    data['namespace'] = data.get('namespace', self.default_namespace)
    trigger['type'] = TRIGGER_STATE
    trigger['entity'] = entity
    data['entity'] = entity
    
    trigger['handle'] = self.api.listen_state(self._state_callback, **data)
    
    if trigger['handle']: self.triggers.append(trigger)
    else: self.error("Trigger no bueno")

  def add_state_trigger(self, state_data):
    entities = state_data.get('entities')
    if isinstance(entities,str): entities = [entities]

    for e in entities:
      self.add_state_trigger_entity(entity = e, state_data = state_data)

  @abstractmethod
  def trigger(self, payload):
    raise NotImplementedError

  def _event_callback(self, event, data, kwargs):
    self.debug("Event {} data {}", event, data)
    for t in self.triggers:
      payload = None
      if t['event'] != event: continue
      if event == EVENT_MQTT: payload = data.get('payload')
      else: payload = data
      if payload: self.trigger(payload)
  
  def _state_callback(self, entity, attribute, old, new, kwargs):
    for t in self.triggers:
      if t['entity'] != entity: continue
      payload = {}
      payload['sentity'] = entity
      payload['attribute'] = attribute
      payload['old'] = old
      payload['new'] = new
      self.trigger(payload)
endregion      

region Constants
OFF = 'OFF'
ON = 'ON'
endregion

region MqttDevice
class MqttDevice(MqttApp):
  state = OFF
  brightness = None

  topic_base = None

  topic_cmd_switch = None
  topic_cmd_brightness = None

  topic_state = None

#  topic_state_switch = None
#  topic_state_brightness = None
  
  def initialize(self):
    super().initialize()
    self.topic_base = self.args.get('topic')
    self.topic_cmd_switch = '/'.join([self.topic_base, "switch"])
    self.topic_state = '/'.join([self.topic_base, "state"])

    self.mqtt.mqtt_unsubscribe(self.topic_cmd_switch)
    self.mqtt.listen_event(self.c_mqtt_cmd_switch, "MQTT_MESSAGE", topic = self.topic_cmd_switch)
    self.mqtt.mqtt_subscribe(self.topic_cmd_switch)
  
  def terminate(self):
    super().terminate()

  def publish_state(self):
    s = {}
    s['state'] = self.state
    if self.state == ON:
      s['brightness'] = self.brightness
    self.mqtt.mqtt_publish(self.topic_state, json.dumps(s))

    # if self.state == ON and self.brightness:
    #   self.set_app_state(self.entity, {"state": self.state, "brightness": self.brightness})
    # else:
    #   self.set_app_state(self.entity, {"state": self.state})

    # entity_id = self.args.get('entity_id')
    # if self.api.entity_exists(entity_id, namespace = "ao"):
    #   self.api.call_service("state/set", entity_id=entity_id, state=self.state.lower(), brightness = self.brightness, namespace = 'ao')
    # else:
    #   self.api.call_service("state/add_entity", entity_id=entity_id, state=self.state.lower(), brightness = self.brightness, namespace = 'ao')



  @abstractmethod
  def _set(self):
    raise NotImplementedError  
  
  @abstractmethod
  def _get(self):
    raise NotImplementedError  

  def c_mqtt_cmd_switch(self, event_name, data, kwargs):
    payload = data.get('payload')
    if payload == ON:
      self.state = ON
      if not self.brightness: self.brightness = 127
    if payload == OFF:
      self.state = OFF
    self._set()
    self.publish_state()
"""
# endregion