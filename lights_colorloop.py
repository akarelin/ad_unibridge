import appdaemon.plugins.hass.hassapi as hass
import json
from datetime import datetime, time

class colorloop(hass.Hass):
  def l(self, message, *args):
    try: debug = self.args["debug"]
    except: debug = False
    if debug: self.log(message.format(*args))

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
    self.l("Switching on")
    self._update()
  def light_off(self):
    self.state = 'OFF'
    self.l("Switching off")
    self._update()

  def _update(self):
    if self.state == 'ON':
      brightness = self.brightness
      self.l("Brightness {}", brightness)

      now=self.datetime()
      midnight=self.datetime().replace(hour=0,minute=0,second=0,microsecond=0)
      seconds=(now-midnight).seconds
      modulo=(seconds%(self.period*60))/10
      self.l("Seconds {}, period {}, modulo {}", seconds, self.period, modulo)

    entities = enumerate(self.args["entities"])
    l = len(self.args["entities"])
    for i,entity in entities:
      if self.state == 'ON':
        hscolor=int((modulo+i*360/l)%360)
        self.l("Setting color for {} to {}", entity, hscolor)
        self.turn_on(entity, hs_color=[hscolor,100], brightness=self.brightness)
      elif self.state == 'OFF':
        self.l("Turning off")
        self.turn_off(entity)
      else:
        self.l("Unkown state {}".format(self.state))
    
    status = {}
    status['state']=self.state
    if self.brightness:
      status['brightness']=self.brightness
    status_json = json.dumps(status)
    if self.topic:
      self.l("Status Publish to Topic {} Payload {}", self.topic, status_json)
      self.call_service("mqtt/publish", topic=self.topic, payload=status_json)
    else:
      self.l("No status topic")