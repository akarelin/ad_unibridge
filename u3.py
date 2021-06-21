# region Imports
import hassapi as hass
import mqttapi as mqtt
import adbase as ad
import adapi as adapi
from abc import ABC, abstractmethod
import logging
import json
import traceback

from datetime import datetime, time
# endregion
# region Constants
EVENT_MQTT = 'MQTT_MESSAGE'

LOG_DEFAULT = 'main_log'
LOG_DEFAULT_MAIN = 'main_log'
LOG_DEFAULT_ERROR = 'error_log'
LOG_DEFAULT_DEBUG = 'debug_log'
LOG_DEFAULT_TRACE = 'trace_log'
LOG_U3_DEBUG = 'u3_debug_log'
LOG_U3 = 'u3_log'
LOG_LINE_LENGTH = 100

DEBUG = 'DEBUG'
INFO = 'INFO'
ERROR = 'ERROR'
WARNING = 'WARNING'
LOG_LEVELS = [DEBUG,INFO,ERROR,WARNING]
LOG_LEVELS_DEBUG = [DEBUG]

T_STATE = 'state'
T_MQTT = 'mqtt'
T_EVENT = 'event'
T_TIMER = 'timer'
# endregion

class U3Base(ad.ADBase):
  api = None
  mqtt = None
  hass = None
  __debug = False

  def initialize(self):
    self.__debug = self.args.get('debug')
    self.api = self.get_ad_api()
    self.mqtt = self.get_plugin_api(self.args.get('mqtt_namespace','mqtt'))
    self.hass = self.get_plugin_api(self.default_namespace)
    self.debug_U3(f"API Handles: {self.api} {self.mqtt} {self.hass}")
  @property
  def default_namespace(self):
    try: namespace = self.api.get_app('globals').default_namespace
    except: namespace = 'default_namespace'
    return namespace
  def Warn(self, msg): self.__log(WARNING, msg)
  def Error(self, msg): self.__log(ERROR, msg)
  def Debug(self, msg): self.__log(DEBUG, msg)
  def debug_U3(self, msg): 
    if self.__debug: self.api.log(msg = msg, log = LOG_U3_DEBUG)
  def log_U3(self, msg): 
    self.api.log(msg = msg, log = LOG_U3)
  def __log(self, level, msg):
    l = level.upper()
    if l not in LOG_LEVELS: self.log_U3(f"Invalid log level {l}")
    elif l in LOG_LEVELS_DEBUG and not self.__debug: return
    else: self.api.log(msg = msg, level = INFO if l in LOG_LEVELS_DEBUG else l, log = LOG_DEFAULT_DEBUG if l in LOG_LEVELS_DEBUG else LOG_DEFAULT)

class Globals(U3Base):
  default_namespace = None
  areas = []
  slugs = {}
  keymap = {}
  insteon = {}
  ''' Example
    creekview:
      module: u3_combines
      class: Globals
      debug: True

      default_namespace: deuce
      areas: []
      keymap:
        kp/AO/AV:
          - appletv
          - htpc
          - atlona
          - 
          - sonos
          - pause
          - speakers
          - tv
        kp/BBQ:
          - 
          - 
          - 
          - 
          - 
          - 
          - 
          - 
      slugs:
        entry: entry
        stairs1: stairs/1
      insteon:
        ignore_events:
        - RR
        - OL
        - ST
    '''

  def get(self, attribute):
    if attribute == 'areas': return self.areas
    elif attribute == 'slugs': return self.slugs
    elif attribute == 'default_namespace': return self.default_namespace
    elif attribute == 'insteon': return self.insteon
    elif attribute == 'keymap': return self.keymap
    else: return None
  def initialize(self):
    super().initialize()
    self.default_namespace = self.args.get('default_namespace')
    self.insteon = self.args.get('insteon')
    self.slugs = [s.lower() for s in self.args.get('slugs')]
    self.areas = [a.lower() for a in self.args.get('areas')]
    self.keymap = self.args.get('keymap')

class U3(U3Base):
  triggers = []
  def initialize(self):
    super().initialize()
    self.add_triggers()
  def terminate(self):
    for t in self.triggers: pass
  def add_triggers(self, triggers = []):
    if not triggers: triggers = self.args.get('triggers')
    if triggers: 
      self.debug_U3(f"Adding triggers {triggers}")
      for t in triggers:
        ttype = t.pop('type',None)
        self.debug_U3(f"    Adding trigger {t}")
        if ttype == T_MQTT: self.add_mqtt_trigger(t)
        elif ttype == T_EVENT: self.add_event_trigger(t)
        elif ttype == T_STATE: self.add_state_trigger(t)
        elif ttype == T_TIMER: self.add_time_trigger(t)
        else: self.error(f"Invalid trigger type {t}")
  @abstractmethod
  def cb_timer(self, data):
    raise NotImplementedError
  @abstractmethod
  def cb_event(self, data):
    raise NotImplementedError
  @abstractmethod
  def cb_mqtt(self, data):
    raise NotImplementedError
  @abstractmethod
  def cb_state(self, entity, attribute, old, new, kwargs):
    raise NotImplementedError
# region Globals
  def glob(self, attribute):
    g = self.api.get_app('globals')
    self.debug_U3(f"Global attribute {attribute}")
    if g and attribute: return g.get(attribute)
    elif g: return g
    else: return None
  @property
  def areas(self):
    return self.glob('areas')
  @property
  def default_namespace(self):
    return self.glob('default_namespace')
  @property
  def keymap(self):
    return self.glob('keymap')
  @property
  def insteon(self):
    return self.glob('insteon')
  @property
  def ignore_events(self):
    return self.glob('insteon').get('ignore_events')
# endregion
# region Callback Internals
  def add_time_trigger(self, trigger):
    start = trigger.get('start',"now")
    interval = trigger.get('interval')
    if not interval: self.error(f"Time trigger: invalid interval {trigger}")
    else: handle = self.api.run_every(self.__cb_timer, start, interval)
    if handle: self.triggers.append({'type': T_TIMER, 'interval': interval, 'start': start, 'handle': handle})
  def __cb_timer(self, data):
    self.cb_timer(data)    

  def add_event_trigger(self, data):
    event = data.pop('event', None)
    if event: handle = self.hass.listen_event(self.__cb_event, event = event, **data)
    if handle: self.triggers.append({'type': T_EVENT, 'handle': handle, 'data': data})
    else: self.Error(f"Event trigger: invalid event {data}")
  def __cb_event(self, event, data, kwargs):
    data['event'] = event
    self.debug_U3(f"Event Callback. Event {event} Data {data} KWARGS {kwargs}")
    self.cb_event(data)

  def add_mqtt_trigger(self, data):
    topic = data.pop('topic', None)
    if topic:
      self.mqtt.mqtt_subscribe(topic)
      handle = self.mqtt.listen_event(callback = self.__cb_mqtt, event = EVENT_MQTT)
      if handle: self.triggers.append({'type': T_MQTT, 'topic': topic, 'handle': handle, 'data': data})
    else: self.Error(f"MQTT trigger: invalid topic {topic}")
  def __cb_mqtt(self, event, data, kwargs):
    if data.get('wildcard'): data['topic'] = data.get('topic').replace(data.get('wildcard'),'')
    self.cb_mqtt(data)

  def add_state_trigger(self, data):
    data['attribute'] = data.get('attribute','all')
    data['namespace'] = data.get('namespace', self.default_namespace)
    handle = self.hass.listen_state(self.__cb_state, **data)
    if handle: self.triggers.append({'type': T_STATE, 'handle': handle, 'data': data})
    else: self.error("Trigger no bueno")
  def __cb_state(self, entity, attribute, old, new, kwargs):
    self.cb_state(entity, attribute, old, new, kwargs)
# endregion

# class U3Disco(U3):
#   pass
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