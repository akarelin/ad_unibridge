import hassapi as hass
import mqttapi as mqtt
import adbase as ad
import adapi as adapi
from abc import ABC, abstractmethod
import logging
import json

from datetime import datetime, time

# region Constants
LOG_PREFIX_NONE = ""
LOG_PREFIX_STATUS = "---"
LOG_PREFIX_ALERT = "***"
LOG_PREFIX_WARNING = "!!!"
LOG_PREFIX_INCOMING = "-->"
LOG_PREFIX_OUTGOING = "<--"

EVENT_MQTT = 'MQTT_MESSAGE'

"""
DEBUG
INFO
WARNING
ERROR
"""
"""
  trace_log:
    filename: /mnt/c/Alex/DEV/AD/logs/trace.log
    format: "{appname} {asctime}: {message}"
    date_format: "%y%m%d %H%M %S" 
"""
LOG_DEFAULT_MAIN = 'main'
LOG_DEFAULT_ERROR = 'error'
LOG_DEFAULT_DEBUG = 'debug'
LOG_UNIBRIDGE_DEBUG = 'unibridge_debug'
LOG_UNIBRIDGE = 'unibridge'
LOG_LINE_LENGTH = 80


T_STATE = 'state'
T_MQTT = 'mqtt'
T_EVENT = 'event'
T_TIMER = 'timer'
# endregion

# region AppBase
class Environment(ad.ADBase):
# region Defaults and Constructor  
  api = None
  mqtt = None
  hass = None
  default_namespace = None
  mqtt_namespace = None

  log_main = LOG_DEFAULT_MAIN
  log_debug = LOG_DEFAULT_DEBUG
  log_error = LOG_DEFAULT_ERROR

  def initialize(self):
    self.api = self.get_ad_api()
    self.default_namespace = self.args.get('default_namespace')
    if self.default_namespace:
      self.hass = self.get_plugin_api(self.default_namespace)
      self._d(f"Hass plugin for {self.default_namespace} initialized as {self.hass}")
    self.mqtt_namespace = self.args.get('mqtt_namespace')
    if self.mqtt_namespace:
      self.mqtt = self.get_plugin_api(self.mqtt_namespace)
      self._d(f"MQTT plugin for {self.mqtt_namespace} initialized as {self.mqtt}")
      
# endregion    

# region Logging for components
  def warn(self, msg):
    self._log("WARNING", LOG_PREFIX_WARNING, msg)

  def error(self, msg):
    self._log("ERROR", LOG_PREFIX_ALERT, msg)

  def debug(self, msg):
    self._log("DEBUG", LOG_PREFIX_STATUS, msg)

  def _log(self, level, prefix, msg):
    l = level.upper()
    if l == 'DEBUG' and not self.args.get("debug"): return
    if l == 'DEBUG':
      log = log_debug
      l = "INFO"
    elif l in ['WARNING']:
      log = log_main
      l = "WARNING"
    else:
      log = log_error
      l = "ERROR"

    m = " ".join([prefix,msg])
    if len(m) > LOG_LINE_LENGTH: m += '\n'

    self.api.log(msg = m, level = l, log = log)
# endregion
# region internal loggin
  def _d(self, msg):
    if not self.args.get("debug"): return
    self.api.log(msg = msg, level = "DEBUG", log = LOG_UNIBRIDGE_DEBUG)

  def _l(self, msg):
    self.api.log(msg = msg, log = LOG_UNIBRIDGE)
# endregion

# region Organizm
  class Organizm(Environment):
    def initialize(self):
      super().initialize()
      self._l(f"Organizm initialized self.")
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
#   triggers = []

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