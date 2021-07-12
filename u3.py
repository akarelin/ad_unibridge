# region Imports
import hassapi as hass
import mqttapi as mqtt
import adbase as ad
import adapi as adapi

import logging
import json
import typing
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod
from datetime import datetime, time
import voluptuous as vol
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

def MQTTCompare(subscription: str, topic: str) -> bool():
  sparts = subscription.split('/')
  tparts = topic.split('/')
  for i, s in enumerate(sparts):
    if s == '#': return True
    elif s == '+': continue
    elif tparts[i] == s: continue
    else: return False

class MqttTopic:
  tparts = []
  
  def __init__(self, t = None, ignore_tparts: Optional[List] = None):
    if t:
      tparts = t.split('/')
      if ignore_tparts:
        for i in ignore_tparts:
          if i in tparts: continue
      if len(tparts) <= 1: return None
      self.tparts = tparts
  def __str__(self):
    return self.topic
  def __add__(self, other):
    return '/'.join(self, other)
  @property
  def wildcard(self) -> bool:
    return True if '#' in self.tparts or '+' in self.tparts else False
  @property
  def topic(self) -> str:
    if self.tparts: return '/'.join(self.tparts)
    else: return None

class U3Base(ad.ADBase):
  api = None 
  mqtt = None
  hass = None
  __debug = False
  
  config = {}
  SCHEMA = vol.Schema({
        vol.Required("module"): str,
        vol.Required("class"): str,
        vol.Remove("dependencies"): any,
        vol.Remove("plugin"): any,
        vol.Optional("default_namespace"): str
      },
      extra=vol.ALLOW_EXTRA
    )

  def initialize(self):
    self.__debug = self.args.get('debug')
    self.api = self.get_ad_api()
    self.mqtt = self.get_plugin_api(self.args.get('default_mqtt_namespace','mqtt'))
    self.hass = self.get_plugin_api('deuce')
  def load(self, schema = {}):
    if schema: self.SCHEMA = self.SCHEMA.extend(schema)
    try: self.config=self.SCHEMA(self.args)
    except: self.error(f"Invalid module configuration {self.args}")

  def P(self, parameter: str): return self.config.get(parameter)
  @property
  def default_namespace(self): return self.args.get('default_namespace','default')
  def Warn(self, msg): self.__log(WARNING, msg)
  def Error(self, msg): self.__log(ERROR, msg)
  def Debug(self, msg): self.__log(DEBUG, msg)
  def Trace(self, logger, msg): self.api.log(msg = msg, level = DEBUG, log = logger)
  def debug_U3(self, msg): 
    if self.__debug: self.api.log(msg = msg, log = LOG_U3_DEBUG)
  def log_U3(self, msg): self.api.log(msg = msg, log = LOG_U3)
  def __log(self, level, msg):
    l = level.upper()
    if l not in LOG_LEVELS: self.log_U3(f"Invalid log level {l}")
    elif l in LOG_LEVELS_DEBUG and not self.__debug: return
    else: self.api.log(msg = msg, level = INFO if l in LOG_LEVELS_DEBUG else l, log = LOG_DEFAULT_DEBUG if l in LOG_LEVELS_DEBUG else LOG_DEFAULT)

class U3(U3Base):
  triggers = []
  universe = None
  def initialize(self):
    super().initialize()
    self.universe = self.api.get_app('universe')
  def load(self, schema = {}):
    super().load(schema)
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
        else: self.Error(f"Invalid trigger type {t}")
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

  def add_time_trigger(self, data):
    start = data.get('start',"now")
    interval = data.get('interval')
    if not interval: self.error(f"Time trigger: invalid interval {data}")
    else: handle = self.api.run_every(self.__cb_timer, start, interval)
    if handle: self.triggers.append({'type': T_TIMER, 'interval': interval, 'start': start, 'handle': handle})
  def __cb_timer(self, data):
    self.cb_timer(data)    

  def add_event_trigger(self, data):
    event = data.pop('event')
    if event: handle = self.hass.listen_event(self.__cb_event, event = event, **data)
    if handle: self.triggers.append({'type': T_EVENT, 'handle': handle, 'event': event, 'data': data})
    else: self.Error(f"Event trigger: invalid event {data}")
  def __cb_event(self, event, data, kwargs):
    data['event'] = event
    self.debug_U3(f"Event Callback. Event {event} Data {data} KWARGS {kwargs}")
    if [t for t in self.triggers if t.get('type') == T_EVENT]: self.cb_event(data)

  def add_mqtt_trigger(self, data):
    topic = data.get('topic')
    if topic:
      topic = topic.lower()
      self.mqtt.mqtt_subscribe(topic)
      handle = self.mqtt.listen_event(self.__cb_mqtt, EVENT_MQTT, wildcard = topic)
      if handle: self.triggers.append({'type': T_MQTT, 'topic': topic, 'handle': handle, 'data': data})
    else: self.Error(f"MQTT trigger: invalid topic {topic}")
  def __cb_mqtt(self, event, data, kwargs):
    self.debug_U3(f"NQTT Callback. Event {event} Data {data} KWARGS {kwargs}")
    topic = data.get('topic')
    if [t for t in self.triggers if t.get('type') == T_MQTT]: self.cb_mqtt(data)
      # s = t.get('topic')
      # if MQTTCompare(s,topic):
      #  self.debug_U3(f"MQTT Event {topic} matched {s}")
      #  self.cb_mqtt(data)
      # else: self.debug_U3(f"MQTT Ignored {data} does not match {s}")

  def add_state_trigger(self, data):
    data['attribute'] = data.get('attribute','all')
    data['namespace'] = data.get('namespace', self.default_namespace)
    handle = self.hass.listen_state(self.__cb_state, **data)
    if handle: self.triggers.append({'type': T_STATE, 'handle': handle, 'data': data})
    else: self.error("Trigger no bueno")
  def __cb_state(self, entity, attribute, old, new, kwargs):
    self.cb_state(entity, attribute, old, new, kwargs)
# endregion

