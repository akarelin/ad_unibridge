import hassapi as hass
import mqttapi as mqtt
import adbase as ad
import adapi as adapi

from datetime import datetime, time

LOG_PREFIX_NONE = ""
LOG_PREFIX_STATUS = "---"
LOG_PREFIX_ALERT = "***"
LOG_PREFIX_WARNING = "!!!"
LOG_PREFIX_INCOMING = "-->"
LOG_PREFIX_OUTGOING = "<--"

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

class App(ad.ADBase):
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
    self.hass = self.get_plugin_api("HASS")
    self.mqtt = self.get_plugin_api("MQTT")
    self.main_log = self.api.get_main_log()
    self.error_log = self.api.get_error_log()

    try: self.trace_log = self.api.get_user_log("trace_log")
    except: self.api.log("Trace_log is not configured")

  def initialize_triggers(self, triggers = []):
    self.debug("Triggers {}", triggers)
    for t in triggers:
      trigger_type = t.get('type')
      if trigger_type == 'event':
        event = t.get('event')
        namespace = t.get('namespace','default')
        self.hass.listen_event(self._trigger_cb, event, namespace = namespace)
      elif trigger_type == 'mqtt':
        topic = t.get('topic')
        self.mqtt.listen_event(self._trigger_cb, "MQTT_MESSAGE", topic = topic)

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
