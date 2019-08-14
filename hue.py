import appdaemon.plugins.hass.hassapi as hass
import json
from datetime import datetime, time

class group(hass.Hass):
  def debug(self, message, *args):
    try:
      if args:
        self.log(message.format(*args), level="DEBUG")
      else:
        self.log(message, level="DEBUG")
    except:
      self.log("Debug Logger Failed {}".format(message))

  def initialize(self):
    self.state = 'OFF'
    self.topic = None
    try: self.brightness = int(self.args["brightness"])
    except: self.brightness = 128
    try: self.rgb_color = self.args["rgb_color"]
    except: self.rgb_color = None

    self.set_namespace(self.args["namespace"])

  def light_on(self, brightness = 128):
    self.state = 'ON'
    self.brightness = brightness
    self.debug("Switching on")
    self._update()
  def light_off(self):
    self.state = 'OFF'
    self.debug("Switching off")
    self._update()

  def _update(self):
    if self.state == 'ON':
      brightness = self.brightness
      self.debug("Brightness {}", brightness)

    entities = enumerate(self.args["entities"])
    l = len(self.args["entities"])
    for i,entity in entities:
      if self.state == 'ON':
        self.turn_on(entity, rgb_color=self.rgb_color, brightness=self.brightness)
      elif self.state == 'OFF':
        self.debug("Turning off")
        self.turn_off(entity)
      else:
        self.debug("Unkown state {}".format(self.state))
    
    status = {}
    status['state']=self.state
    if self.brightness:
      status['brightness']=self.brightness
    if self.rgb_color:
      status['rgb_color']=self.rgb_color
    status_json = json.dumps(status)
    if self.topic:
      self.debug("Status Publish to Topic {} Payload {}", self.topic, status_json)
      self.call_service("mqtt/publish", topic=self.topic, payload=status_json)
    else:
      self.debug("No status topic")

class loop(hass.Hass):
  def debug(self, message, *args):
    try:
      if args:
        self.log(message.format(*args), level="DEBUG")
      else:
        self.log(message, level="DEBUG")
    except:
      self.log("Debug Logger Failed {}".format(message))

  def initialize(self):
    self.state = 'OFF'
    self.topic = None
    try: self.period = int(self.args["period"])
    except: self.period = 60
    try: self.precision = int(self.args["precision"])
    except: self.precision = 5
    try: self.brightness = int(self.args["brightness"])
    except: self.brightness = 128

    self.set_namespace(self.args["namespace"])
    self.timer = self.run_every(self.cbTimer, self.datetime(), self.precision)
  def terminate(self):
    self.cancel_timer(self.timer)
  def cbTimer(self, kwargs):
    self._update()

  def light_on(self, brightness = 128):
    self.state = 'ON'
    self.brightness = brightness
    self.debug("Switching on")
    self._update()
  def light_off(self):
    self.state = 'OFF'
    self.debug("Switching off")
    self._update()

  def _update(self):
    if self.state == 'ON':
      brightness = self.brightness
      self.debug("Brightness {}", brightness)

      now=self.datetime()
      midnight=self.datetime().replace(hour=0,minute=0,second=0,microsecond=0)
      seconds=(now-midnight).seconds
      modulo=(seconds%(self.period*60))/10
      self.debug("Seconds {}, period {}, modulo {}", seconds, self.period, modulo)

    entities = enumerate(self.args["entities"])
    l = len(self.args["entities"])
    for i,entity in entities:
      if self.state == 'ON':
        hscolor=int((modulo+i*360/l)%360)
        self.debug("Setting color for {} to {}", entity, hscolor)
        self.turn_on(entity, hs_color=[hscolor,100], brightness=self.brightness)
      elif self.state == 'OFF':
        self.debug("Turning off")
        self.turn_off(entity)
      else:
        self.debug("Unkown state {}".format(self.state))
    
    status = {}
    status['state']=self.state
    if self.brightness:
      status['brightness']=self.brightness
    status_json = json.dumps(status)
    if self.topic:
      self.debug("Status Publish to Topic {} Payload {}", self.topic, status_json)
      self.call_service("mqtt/publish", topic=self.topic, payload=status_json)
    else:
      self.debug("No status topic")      