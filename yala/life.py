# region Imports
import appdaemon.plugins.hass.hassapi as hass
import appdaemon.plugins.mqtt.mqttapi as mqtt
import appdaemon.adbase as ad
import appdaemon.adapi as adapi
from abc import ABC, abstractmethod
import logging
import json

from datetime import datetime, time
import voluptuous as vol
# endregion
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

# region Environment
AD_SCHEMA = vol.Schema({
    vol.Required("class"): str,
    vol.Required("module"): str,
    vol.Optional("constrain_start_time"): str,
    vol.Optional("constrain_end_time"): str,
    vol.Optional("global_dependencies"): str,
    vol.Optional("constrain_input_boolean"): str,
  })

ENVIRONMENT_SCHEMA = AD_SCHEMA.extend({
    vol.Required("default_namespace"): str,
    vol.Required("mqtt_namespace"): str
  })

class Environment(ad.ADBase):
# region Defaults and Constructor  
  api = None
  log_main = LOG_DEFAULT_MAIN
  log_debug = LOG_DEFAULT_DEBUG
  log_error = LOG_DEFAULT_ERROR

  mqtt = None
  hass = None
  default_namespace = None
  mqtt_namespace = None

  def initialize(self):
#    self.args = ENVIRONMENT_SCHEMA(self.args)
    self.log_main = LOG_DEFAULT_MAIN
    self.log_debug = LOG_DEFAULT_DEBUG
    self.log_error = LOG_DEFAULT_ERROR
    self.api = self.get_ad_api()

    self.default_namespace = self.args.get('default_namespace')
    self.mqtt_namespace = self.args.get('mqtt_namespace')

    if self.default_namespace:
      self.hass = self.get_plugin_api(self.default_namespace)
      self._d(f"Hass plugin for {self.default_namespace} initialized as {self.hass}")
    if self.mqtt_namespace:
      self.mqtt = self.get_plugin_api(self.mqtt_namespace)
      self._d(f"MQTT plugin for {self.mqtt_namespace} initialized as {self.mqtt}")
  def terminate(self):
    pass
# endregion    
# region Logging for components
  def warn(self, msg):
    self.__log("WARNING", LOG_PREFIX_WARNING, msg)
  def error(self, msg):
    self.__log("ERROR", LOG_PREFIX_ALERT, msg)
  def debug(self, msg):
    self.__log("DEBUG", LOG_PREFIX_STATUS, msg)

  def __log(self, level, prefix, msg):
    l = level.upper()
    if l == 'DEBUG' and not self.debug: return
    if l == 'DEBUG':
      log = self.log_debug
      l = "INFO"
    elif l in ['WARNING']:
      log = self.log_main
      l = "WARNING"
    else:
      log = self.log_error
      l = "ERROR"
    m = " ".join([prefix,msg])
    if len(m) > LOG_LINE_LENGTH: m += '\n'
    self.api.log(msg = m, level = l, log = log)
# endregion
# region internal logging
  def _d(self, msg):
    if not self.debut: return
    self.api.log(msg = msg, level = "DEBUG", log = LOG_UNIBRIDGE_DEBUG)

  def _l(self, msg):
    self.api.log(msg = msg, log = LOG_UNIBRIDGE)
# endregion
# endregion


# region Organizm
class Organizm(Environment):
  __force_refresh_interval = 1*60*60
  __refresh_interval = 1*60
  timers = []
 
  def initialize(self):
    super().initialize()
    self._l(f"Organizm initialized self.")
    self.debug(f"Organizm initialized")
  def terminate(self):
    for t in self.timers:
      self.api.cancel_timer(t)
    super().terminate()
  def __initialize(self):
    self.timers.append(self.api.run_every(self.__c_force_refresh, "now+30", __force_refresh_interval))
    self.timers.append(self.api.run_every(self.__c_refresh, "now+1", __refresh_interval))
  def __c_force_refresh(self, kwargs):
    self.refresh(force = True)
  def __c_refresh(self, kwargs):
    self.refresh()

  @abstractmethod
  def refresh(self, force = False):
    raise NotImplementedError
# endregion
