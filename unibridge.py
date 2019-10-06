import hassapi as hass
import mqttapi as mqtt
import adbase as ad
import adapi as adapi
from abc import ABC, abstractmethod

from datetime import datetime, time

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
LOG_DEBUG = 'debug_log'
LOG_LINE_LENGTH = 80

class AppBase(ad.ADBase):
  api = None

  def initialize(self):
    self.api = self.get_ad_api()

  def warn(self, message, *args):
    self._log("WARNING", LOG_PREFIX_WARNING, message, *args)

  def error(self, message, *args):
    self._log("ERROR", LOG_PREFIX_ALERT, message, *args)

  def debug(self, message, *args):
    self._log("DEBUG", LOG_PREFIX_STATUS, message, *args)

  def _log(self, level, prefix, message, *args):
    l = level.upper()
    if l == 'DEBUG' and not self.args.get("debug"): return

    m = " ".join([prefix,message.format(*args)])
    if len(m) > LOG_LINE_LENGTH: m += '\n'

    if l == 'DEBUG': self.api.log(msg = m, level = "INFO", log = LOG_DEBUG)
    else: self.api.log(msg = m, level = l)

class App(AppBase):
  default_namespace = None
  default_mqtt_namespace = None
  hass = None
  mqtt = None
  trigger_data = []

  def initialize(self):
    super().initialize()
    self.default_namespace = self.args.get('default_namespace','default')
    self.default_mqtt_namespace = self.args.get('default_mqtt_namespace','default_mqtt')
    self.hass = self.get_plugin_api(self.default_namespace)
    self.mqtt = self.get_plugin_api(self.default_mqtt_namespace)
    self.initialize_triggers()

  def terminate(self):
    for t in self.trigger_data:
      if t['type'] == 'event':
        self.hass.cancel_listen_event(t['handle'])
      elif t['type'] == 'mqtt':
        self.mqtt.cancel_listen_event(t['handle'])
  
  def initialize_triggers(self, triggers = []):
    if not triggers: triggers = self.args.get('triggers')
    if not triggers: return
   
    self.debug("Triggers {}", triggers)
    for t in triggers:
      trigger = {}
      trigger['type'] = t.get('type')

      trigger['payload_type'] = t.get('payload_type','raw')
      if trigger['payload_type'] in ['json']:
        trigger['key'] = t.get('key')
        if not trigger['key']:
          self.warn("Unknown key {}", trigger['key'])
          continue
      
      if trigger['type'] == 'event':
        trigger['namespace'] = t.get('namespace',self.default_namespace)
        trigger['event'] = t.get('event')
        trigger['handle'] = self.hass.listen_event(self._event_callback, event = trigger['event'], namespace = trigger['namespace'])
      elif trigger['type'] == 'mqtt':
        trigger['topic'] = t.get('topic')
        trigger['namespace'] = t.get('namespace',self.default_mqtt_namespace)
        trigger['event'] = EVENT_MQTT
        trigger['handle'] = self.mqtt.listen_event(self._event_callback, event = trigger['event'], topic = trigger['topic'])
      self.trigger_data.append(trigger)

  @abstractmethod
  def trigger(self, payload):
    raise NotImplementedError

  def _event_callback(self, event, data, kwargs):
    for t in self.trigger_data:
      payload = None
      if t['event'] != event: continue
      if event == EVENT_MQTT: payload = data.get('payload')
      else: payload = data
      if payload: self.trigger(payload)