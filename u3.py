import hassapi as hass
import mqttapi as mqtt
import adbase as ad
import adapi as adapi
from abc import ABC, abstractmethod
import logging
import json
import traceback

from datetime import datetime, time
  
# region Constants
EVENT_MQTT = 'MQTT_MESSAGE'

LOG_DEFAULT = 'main_log'
LOG_DEFAULT_MAIN = 'main_log'
LOG_DEFAULT_ERROR = 'error_log'
LOG_DEFAULT_DEBUG = 'debug_log'
LOG_U3_DEBUG = 'u3_debug'
LOG_U3 = 'u3'
LOG_LINE_LENGTH = 100

T_STATE = 'state'
T_MQTT = 'mqtt'
T_EVENT = 'event'
T_TIMER = 'timer'
# endregion

# region U3Base
class U3Base(ad.ADBase):
# region Defaults and Constructor  
  api = None
  mqtt = None
  hass = None
  default_namespace = None
  triggers = []

  def initialize(self):
    self.api = self.get_ad_api()
    self.default_namespace = self.args.get('default_namespace')
#    self.api.log(f"AD API Handle: {self.api}")
#    self.debug(f"AD API Handle: {self.api}")

#    if self.default_namespace:
#      self.hass = self.hass.get_ad_api()
    self.mqtt = self.get_plugin_api(self.args.get('mqtt_namespace','mqtt'))
    self.hass = self.get_plugin_api(self.args.get('default_namespace'))
    self.debug(f"API Handles: {self.api} {self.mqtt} {self.hass}")
    self.add_triggers()
    self._d(f"Triggers {self.triggers}")

  def terminate(self):
    for t in self.triggers: pass      

# endregion    
# region Logging
  def warn(self, msg): self._log("WARNING", msg)
  def error(self, msg): self._log("ERROR", msg)
  def debug(self, msg): self._log("DEBUG", msg)

  def _log(self, level, msg):
    l = level.upper()
    if l == 'DEBUG' and not self.args.get("debug"): return
    if l == 'DEBUG':
      log = LOG_DEFAULT_DEBUG
      l = "INFO"
    elif l in ['WARNING']:
      log = LOG_DEFAULT
      l = "WARNING"
    else:
      log = LOG_DEFAULT
      l = "ERROR"
    if len(msg) > LOG_LINE_LENGTH: msg += '\n'
    self.api.log(msg = msg, level = l, log = log)
  def _d(self, msg): 
    if self.args.get("debug"): self.api.log(msg = msg, log = LOG_U3_DEBUG)
  def _l(self, msg): 
    self.api.log(msg = msg, log = LOG_U3)

  def _trace(self, module, msg):
    if not self.args.get("trace"): return
    if module not in ['linter']: return
    log = "trace_" + module
    self.api.log(msg = msg, level = 'DEBUG', log = log)
  
  def trace(self, msg):
    self._trace(module = self.__class__.__name__, msg = msg)
# endregion
# region Triggers
  def add_triggers(self, triggers = []):
    if not triggers: triggers = self.args.get('triggers')
    if not triggers: return
    self._d(f"Adding triggers {triggers}")
   
    for t in triggers:
      self._d(f"Adding trigger {t}")
      if t['type'] == T_MQTT: self.add_mqtt_trigger(t)
      elif t['type'] == T_EVENT: self.add_event_trigger(t)
      elif t['type'] == T_STATE: self.add_state_trigger(t)
      elif t['type'] == T_TIMER: self.add_time_trigger(t)
      else: self.error(f"Invalid trigger type {t}")

  def add_time_trigger(self, trigger):
    t = {}
    t['type'] = T_TIMER
    interval = trigger.get('interval')
    if not interval:
      self.error("Unknown trigger {}", trigger)
      return
    t['interval'] = interval
    start = trigger.get('start',"now")
    t['start'] = start
    t['handle'] = self.api.run_every(self._timer_callback, start, interval)
    self.triggers.append(t)

  def add_event_trigger(self, data):
    t = {}
    t['type'] = T_EVENT
    t['namespace'] = data.get('namespace',self.default_namespace)
    event = data.pop('event')
    self._d(f"Adding event {event} trigger {data}")
    t['handle'] = self.hass.listen_event(self._event_callback, event = event, **data)
    if t['handle']: self.triggers.append(t)
    else: self.error("Trigger no bueno")

  def add_mqtt_trigger(self, data):
    t = {}
    t['type'] = T_MQTT
    topic = data.pop('topic')
    self.mqtt.mqtt_subscribe(topic)

    c = {}
#    c['event'] = 'MQTT_MESSAGE'
    if '#' in topic or '+' in topic: c['wildcard'] = topic
    elif topic: c['topic'] = topic
    self._d(f"MQTT Trigger {data} ==> {c}")

### DEBUG
#    t['handle'] = self.mqtt.listen_event(self._mqtt_callback, "MQTT_MESSAGE")
#    if t['handle']: self.triggers.append(t)

# MQTT Event    
#    t['handle'] = self.mqtt.listen_event(self._mqtt_callback, "MQTT_MESSAGE", c)
    t['handle'] = self.mqtt.listen_event(self._mqtt_callback, "MQTT_MESSAGE", wildcard = '#')
    self._d(f"Adding mqtt trigger {c} from {data}")
    if t['handle']: self.triggers.append(t)
    else: self.error("Trigger no bueno")

    t['handle'] = self.mqtt.listen_event(self._mqtt_callback, "MQTT_MESSAGE", wildcard = 'i1/#')
    self._d(f"Adding mqtt trigger {c} from {data}")
    if t['handle']: self.triggers.append(t)
    else: self.error("Trigger no bueno")

# AD Event    
    # t['handle'] = self.api.listen_event(self._event_callback, **c)
    # self._d(f"Adding AD trigger {c} from {data}")
    # if t['handle']: self.triggers.append(t)
    # else: self.error("Trigger no bueno")

  def add_state_trigger(self, data):
    raise NotImplementedError
# endregion
# region Internals
  def _mqtt_callback(self, event, data, kwargs):
#    self._d(f"MQTT Callback. Event {event} Data {data} KWARGS {kwargs}")
    if 'i1/kp' in data.get('topic'):
      self._d(f"Keypad detected {data.get('topic')}")
      self.Callback(T_MQTT, data)
#    else: self._d(f"Not our topic {data.get('topic')}")
  def _event_callback(self, event, data, kwargs):
    data['event'] = event
    self._d(f"Event Callback. Event {event} Data {data} KWARGS {kwargs}")
    self.Callback(T_EVENT, data)
  def _timer_callback(self, data):
    self.Callback(T_TIMER, data)    
  @abstractmethod
  def Callback(self, type, data):
    raise NotImplementedError
# endregion
# endregion

# # region MqttApp
# class MqttApp(AppBase):
#   triggers = []
  
#   def initialize(self):
#     super().initialize()
#     self.mqtt = self.get_plugin_api(self.args.get('mqtt_namespace','mqtt'))
#     self.hass = self.get_plugin_api(self.args.get('default_namespace'))
#     self.debug("Triggers {}", self.args.get('triggers'))
#     self.add_triggers()
  
#   def terminate(self):
#     for t in self.triggers:
#       if t.get('type') == TRIGGER_TIMER:
#         return

#   def add_triggers(self, triggers = []):
#     if not triggers: triggers = self.args.get('triggers')
#     if not triggers: return
   
#     self.debug("Triggers {}", triggers)
#     for t in triggers:
#       if t['type'] == TRIGGER_TIMER: self.add_time_trigger(t)
#       else:
#         self.error("Invalid trigger type {}", t)
#         continue

#   def add_time_trigger(self, trigger):
#     t = {}
#     t['type'] = TRIGGER_TIMER
#     interval = trigger.get('interval')
#     if not interval:
#       self.error("Unknown trigger {}", trigger)
#       return
#     t['interval'] = interval
#     start = trigger.get('start',"now")
#     t['start'] = start
#     t['handle'] = self.api.run_every(self.trigger, start, interval)
#     self.triggers.append(t)

#   @abstractmethod
#   def trigger(self, payload):
#     raise NotImplementedError
# # endregion

# # region App
# class App(AppBase):
#   triggers = []self.mqtt.listen_event

#   def initialize(self):
#     super().initialize()
#     self.hass = self.get_plugin_api(self.default_namespace)

#     self.debug("Namespace {} hass {}", self.default_namespace, self.hass)    

#     self.mqtt = self.get_plugin_api(self.default_mqtt_namespace)
#     self.add_triggers()

#   def terminate(self):
#     for t in self.trigger_data:
#       if t['type'] == TRIGGER_EVENT:
#         self.hass.cancel_listen_event(t['handle'])
#       elif t['type'] == TRIGGER_MQTT:
#         self.mqtt.cancel_listen_event(t['handle'])

#   def add_triggers(self, triggers = []):
#     if not triggers: triggers = self.args.get('triggers')
#     if not triggers: return
   
#     self.debug("Triggers {}", triggers)
#     for t in triggers:
#       if t['type'] == TRIGGER_MQTT:
#         t['event'] = EVENT_MQTT
#         self.add_event_trigger(t)
#       elif t['type'] == TRIGGER_EVENT: self.add_event_trigger(t)
#       elif t['type'] == TRIGGER_STATE: self.add_state_trigger(t)
#       else:
#         self.error("Invalid trigger type {}",t)
#         continue
  
#   def add_event_trigger(self, event_data):
#     data = event_data
#     if 'event' not in data:
#       data['event'] = EVENT_MQTT
#     self.debug("Adding event trigger {}", event_data)
#     trigger = {}
#     trigger['event'] = data['event']

#     if not data.get('namespace'):
#       if data['event'] == EVENT_MQTT: data['namespace'] = self.default_mqtt_namespace
#       else: data['namespace'] = self.default_namespace

#     if data['event'] == EVENT_MQTT:
#       trigger['type'] = TRIGGER_MQTT
#       trigger['handle'] = self.mqtt.listen_event(self._event_callback, **data)
#     else:
#       trigger['type'] = TRIGGER_EVENT
#       trigger['handle'] = self.hass.listen_event(self._event_callback, **data)

#     if trigger['handle']: self.triggers.append(trigger)
#     else: self.error("Trigger no bueno")

#   def add_state_trigger_entity(self, entity, state_data):
#     data = state_data
#     trigger = {}

#     data['namespace'] = data.get('namespace', self.default_namespace)
#     trigger['type'] = TRIGGER_STATE
#     trigger['entity'] = entity
#     data['entity'] = entity
    
#     trigger['handle'] = self.api.listen_state(self._state_callback, **data)
    
#     if trigger['handle']: self.triggers.append(trigger)
#     else: self.error("Trigger no bueno")

#   def add_state_trigger(self, state_data):
#     entities = state_data.get('entities')
#     if isinstance(entities,str): entities = [entities]

#     for e in entities:
#       self.add_state_trigger_entity(entity = e, state_data = state_data)

#   @abstractmethod
#   def trigger(self, payload):
#     raise NotImplementedError

#   def _event_callback(self, event, data, kwargs):
#     self.debug("Event {} data {}", event, data)
#     for t in self.triggers:
#       payload = None
#       if t['event'] != event: continue
#       if event == EVENT_MQTT: payload = data.get('payload')
#       else: payload = data
#       if payload: self.trigger(payload)
  
#   def _state_callback(self, entity, attribute, old, new, kwargs):
#     for t in self.triggers:
#       if t['entity'] != entity: continue
#       payload = {}
#       payload['sentity'] = entity
#       payload['attribute'] = attribute
#       payload['old'] = old
#       payload['new'] = new
#       self.trigger(payload)
# # endregion      

# # region Constants
# OFF = 'OFF'
# ON = 'ON'
# # endregion

# # region MqttDevice
# class MqttDevice(MqttApp):
#   state = OFF
#   brightness = None

#   topic_base = None

#   topic_cmd_switch = None
#   topic_cmd_brightness = None

#   topic_state = None

# #  topic_state_switch = None
# #  topic_state_brightness = None
  
#   def initialize(self):
#     super().initialize()
#     self.topic_base = self.args.get('topic')
#     self.topic_cmd_switch = '/'.join([self.topic_base, "switch"])
#     self.topic_state = '/'.join([self.topic_base, "state"])

#     self.mqtt.mqtt_unsubscribe(self.topic_cmd_switch)
#     self.mqtt.listen_event(self.c_mqtt_cmd_switch, "MQTT_MESSAGE", topic = self.topic_cmd_switch)
#     self.mqtt.mqtt_subscribe(self.topic_cmd_switch)
  
#   def terminate(self):
#     super().terminate()

#   def publish_state(self):
#     s = {}
#     s['state'] = self.state
#     if self.state == ON:
#       s['brightness'] = self.brightness
#     self.mqtt.mqtt_publish(self.topic_state, json.dumps(s))

#     # if self.state == ON and self.brightness:
#     #   self.set_app_state(self.entity, {"state": self.state, "brightness": self.brightness})
#     # else:
#     #   self.set_app_state(self.entity, {"state": self.state})

#     # entity_id = self.args.get('entity_id')
#     # if self.api.entity_exists(entity_id, namespace = "ao"):
#     #   self.api.call_service("state/set", entity_id=entity_id, state=self.state.lower(), brightness = self.brightness, namespace = 'ao')
#     # else:
#     #   self.api.call_service("state/add_entity", entity_id=entity_id, state=self.state.lower(), brightness = self.brightness, namespace = 'ao')



#   @abstractmethod
#   def _set(self):
#     raise NotImplementedError  
  
#   @abstractmethod
#   def _get(self):
#     raise NotImplementedError  

#   def c_mqtt_cmd_switch(self, event_name, data, kwargs):
#     payload = data.get('payload')
#     if payload == ON:
#       self.state = ON
#       if not self.brightness: self.brightness = 127
#     if payload == OFF:
#       self.state = OFF
#     self._set()
#     self.publish_state()
# # endregion