import hassapi as hass
import mqttapi as mqtt
import adbase as ad
import adapi as adapi

from datetime import datetime, time

#from appdaemon.utils import __version__ as AD_VERSION

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
    api = self.get_ad_api()
    api.log(m, level=l)

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

#  def __init__(self):
#    self.ad = self.get_ad_api()
#    self.ad.log("Is it???")
  # def initialize(self):
  #   self.api = self.get_ad_api()
  #   self.api.log("Is it???")
#  def terminate(self):

# class mqtt(unibridge.AppMqtt):
#   self.topics = []

#   def subscribe(self, topic):
#     if topic not in self.topics:
#       self.topics.append(topic)
#     self.mqtt_subscribe(topic)
  
#   def unsibscribe(self, topic):
#     if topic in self.topics:
#       self.topics.remove(topic)
#     self.mqtt_unsubscribe(topic)

#   def initialize(self):
# #    try: self.topics = self.args["topics"]
# #    except: self.topics = ["#"]
#     self.set_namespace(self.args['namespace'])
# #    for t in self.topics:
# #      self.mqtt_subscribe(t)
#   def terminate(self):
#     for topic in self.topics:
#       self.mqtt_unsubscribe(topic)

# class AppHass(hassapi.Hass):
#   class Meta:
#     """
#     Unibridge Hass Base Class
#     """
#     name = "Unibridge Hass"

#   def _log(self, level, prefix, message, *args):
#     l = level.upper()
#     try:
#       m = message.format(*args)
#       if len(prefix) > 0:
#         m = prefix+" "+m
#     except:
#       l = "WARNING"
#       m = "{} Invalid message: {}".format(LOG_PREFIX_WARNING,message)

#     super().log(m, level=l)

#   def warn(self, message, *args):
#     self._log("WARNING", LOG_PREFIX_WARNING, message, *args)

#   def error(self, message, *args):
#     self._log("ERROR", LOG_PREFIX_ALERT, message, *args)

#   def debug(self, message, *args):
#     try: 
#       if self.args.get("debug"):
#         self._log("INFO", LOG_PREFIX_STATUS, message, *args)
#     except:
#       self._log("ERROR", LOG_PREFIX_WARNING, "Exception with debug")

# class AppMqtt(mqttapi.Mqtt):
#   class Meta:
#     """
#     Unibridge MQTT Base Class
#     """
#     name = "Unibridge MQTT"

#   def _log(self, level, prefix, message, *args):
#     l = level.upper()
#     try:
#       m = message.format(*args)
#       if len(prefix) > 0:
#         m = prefix+" "+m
#     except:
#       l = "WARNING"
#       m = "{} Invalid message: {}".format(LOG_PREFIX_WARNING,message)
#     super().log(m, level=l)

#   def warn(self, message, *args):
#     self._log("WARNING", LOG_PREFIX_WARNING, message, *args)

#   def error(self, message, *args):
#     self._log("ERROR", LOG_PREFIX_ALERT, message, *args)

#   def debug(self, message, *args):
#     try: 
#       if self.args.get("debug"):
#         self._log("INFO", LOG_PREFIX_STATUS, message, *args)
#     except:
#       self._log("ERROR", LOG_PREFIX_WARNING, "Exception with debug")
