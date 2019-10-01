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

class AppBase(ad.ADBase):
  def _log(self, level, prefix, message, *args):
    l = level.upper()
    try:
      m = message.format(*args)
      if len(prefix) > 0:
        m = prefix+" "+m
    except:
      l = "WARNING"
      m = "{} Invalid message: {}".format(LOG_PREFIX_WARNING,message)
    if l in ['DEBUG']:
#      self.trace_log.log(msg = m)
      self.api.log(m, log="trace_log")
    elif l in ['WARNING','INFO']:
#      self.main_log.log(msg = m)
      self.api.log(m, level = l)
    elif l in ['ERROR']:
#      self.error_log.log(msg = m)
      self.api.log(m, level = l)
    else:
#      self.error_log.log(msg = m)
      self.api.log(m, level = l)

  def warn(self, message, *args):
    self._log("WARNING", LOG_PREFIX_WARNING, message, *args)

  def error(self, message, *args):
    self._log("ERROR", LOG_PREFIX_ALERT, message, *args)

  def debug(self, message, *args):
    try: 
      if self.args.get("debug"):
        self._log("INFO", LOG_PREFIX_STATUS, message, *args)
    except:
      self._log("ERROR", LOG_PREFIX_WARNING, "Exception with debug")

  def initialize(self):
    self.api = self.get_ad_api()
    self.main_log = self.api.get_main_log()
    self.error_log = self.api.get_error_log()
    try: self.trace_log = self.api.get_user_log("trace_log")
    except: self.api.log("Trace_log is not configured")

class App(AppBase):
  def initialize(self):
    self.default_namespace = self.args.get('default_namespace','default')
    self.default_mqtt_namespace = self.args.get('default_mqtt_namespace','default_mqtt')
    self.hass = self.get_plugin_api(self.default_namespace)
    self.mqtt = self.get_plugin_api(self.default_mqtt_namespace)

  trigger_data = []

  def initialize_triggers(self, triggers = []):
    self.debug("Triggers {}", triggers)
    for t in triggers:
      self.debug("Trigger!!!! {}",t)
      trigger = {}
      trigger['type'] = t.get('type')

      trigger['payload_type'] = t.get('payload_type','raw')
      if trigger['payload_type'] == 'json':
        trigger['key'] = t.get('key')
        if not trigger['key']:
          self.warn("Unknown key {}", trigger['key'])
          continue

      if trigger['type'] == 'event':
        trigger['namespace'] = t.get('namespace',self.default_namespace)
        trigger['event'] = t.get('event')
        trigger['handle'] = self.hass.listen_event(self._cb_event, trigger['event'], namespace = trigger['namespace'])
      elif trigger['type'] == 'mqtt':
        trigger['topic'] = t.get('topic')
        trigger['namespace'] = t.get('namespace',self.default_mqtt_namespace)
        trigger['event'] = EVENT_MQTT
        trigger['handle'] = self.mqtt.listen_event(self._cb_event, trigger['event'], topic = trigger['topic'])
      self.trigger_data.append(trigger)

  @abstractmethod
  def _event(self, value):
    raise NotImplementedError

  def _cb_event(self, *args):
    event = args[0]
    data = args[1]
    
    self.debug("Super-callback {} with data {}", event, data)

    i = 0
    for t in self.trigger_data:
      i = i + 1
      self.debug("Trigger #{} {}",i,t)

      payload = None
      value = None
      if t['event'] != event: continue
      if event == EVENT_MQTT:
        payload = data.get('payload')
      else:
        payload = data
      
      if t['payload_type'] == 'json':
        value = payload.get(t['key'])
      else:
        value = payload

      if value: 
        self.debug("Trigger #{} Acceppted",i)
        self._event(value)

  # def _trigger_cb(self, *args, **kwargs):
  #   self.debug("Data {} kwargs {}", *args, **kwargs)
    # def _mqtt(self, event_name, data, kwargs):
    # self.debug("MQTT event {}",data)
    # if data.get('topic') not in self.topics:
    #   return
    # scene = data.get('payload')
    # if scene in self.scene_list:
    #   self.DoIt(scene)
    # else:
    #   self.warn("Unknown payload {}", scene)


