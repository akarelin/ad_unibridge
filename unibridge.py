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
    self.api.log(m, level=l)

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