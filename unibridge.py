#from appdaemon.plugins.hass import hassapi
#import appdaemon.plugins.mqtt.mqttapi as mqtt
from appdaemon.plugins.hass import hassapi
from appdaemon.plugins.mqtt import mqttapi
from datetime import datetime, time

from appdaemon.utils import __version__ as AD_VERSION

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

class AppHass(hassapi.Hass):
    class Meta:
        """
        Unibridge Hass Base Class
        """
        name = "Unibridge Hass"

    def _log(self, level, prefix, message, *args):
        l = level.upper()
        try:
            m = message.format(*args)
            if len(prefix) > 0:
                m = prefix+" "+m
        except:
            l = "WARNING"
            m = "{} Invalid message: {}".format(LOG_PREFIX_WARNING,message)

        super().log(m, level=l)

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

class AppMqtt(mqttapi.Mqtt):
    class Meta:
        """
        Unibridge MQTT Base Class
        """
        name = "Unibridge MQTT"

    def _log(self, level, prefix, message, *args):
        l = level.upper()
        try:
            m = message.format(*args)
            if len(prefix) > 0:
                m = prefix+" "+m
        except:
            l = "WARNING"
            m = "{} Invalid message: {}".format(LOG_PREFIX_WARNING,message)

        super().log(m, level=l)

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
