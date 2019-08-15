#import appdaemon.plugins.hass.hassapi as hass
import unibridge
import json
from datetime import datetime, time

"""
bedroom_ambient:
  module: hue
  class: group

  name: "Bedroom Lamps"
  topic: 'bedroom/ambient'
  mqtt_namespace: sway_mqtt

  entities:
    - light.hue_bedroom
  rgb_color: [255,116,22]
  namespace: sway_hassio

bedroom_ambient_mqtt:
  module: mqtt_light
  class: mqtt_light
  dependencies:
    - bedroom_ambient
  parent: bedroom_ambient
"""

class group(unibridge.AppHass):
  def initialize(self):
    self.state = 'OFF'
    self.brightness = 0
    self.topic_state = None
    self.topic_set = None
    self.init()

  def init(self):
    self.set_namespace(self.args["namespace"])
    self.entities = []
    self.entities = self.args["entities"]
    self.entity_count = len(self.args["entities"])

    try: self.brightness = int(self.args["brightness"])
    except: self.brightness = 128

    try: self.rgb_color = self.args["rgb_color"]
    except: self.rgb_color = None

    try: self.effect = self.args["effect"]
    except: self.effect = None
    
    if self.effect == 'colorloop':
      self.init_colorloop()
  
  def init_colorloop(self):
    try: self.period = int(self.args["period"])
    except: self.period = 60
    try: self.precision = int(self.args["precision"])
    except: self.precision = 5
    self.timer = self.run_every(self._timer, self.datetime(), self.precision)

  def light_on(self, brightness = 128):
    self.state = 'ON'
    self.brightness = brightness
    self.debug("Switching on")
    self._set()
  def light_off(self):
    self.state = 'OFF'
    self.debug("Switching off")
    self._set()

  def _set(self):
    self.debug("Setting entities {} effect {}",self.entities,self.effect)
    if self.effect == 'colorloop':
      self._set_colorloop()
    else:
      self._set_color()
    self._publish()
  
  def _set_color(self):
    self.debug("Setting entities {}, brightness {}, color",self.entities,self.brightness,self.rgb_color)
    for i,entity in enumerate(self.entities):
      if self.state == 'ON':
        self.debug("Turning on entity {}, brightness {}, color",entity,self.brightness,self.rgb_color)
        self.turn_on(entity, rgb_color=self.rgb_color, brightness=self.brightness)
      elif self.state == 'OFF':
        self.debug("Turning off entity {}",entity)
        self.turn_off(entity)
      else:
        self.debug("Unkown state {}".format(self.state))
   
  def _set_colorloop(self):
    now=self.datetime()
    seconds=(now-self.datetime().replace(hour=0,minute=0,second=0,microsecond=0)).seconds
    modulo=(seconds%(self.period*60))/10

    e = enumerate(self.entities)
    for i,entity in enumerate(self.entities):
      if self.state == 'ON':
        hscolor=int((modulo+i*360/self.entity_count)%360)
        self.turn_on(entity, hs_color=[hscolor,100], brightness=self.brightness)
      elif self.state == 'OFF':
        self.turn_off(entity)
      else:
        self.error("Unkown state {}".format(self.state))

  def _publish(self):
    status = {}
    status['state']=self.state
    if self.state == 'ON':
      if self.brightness:
        status['brightness']=self.brightness
      if self.rgb_color:
        status['rgb_color']=self.rgb_color
    status_json = json.dumps(status)
    if self.topic_state:
      self.debug("Status Publish to Topic {} Payload {}", self.topic_state, status_json)
      self.call_service("mqtt/publish", topic=self.topic_state, payload=status_json)
    else:
      self.debug("No status topic")

  def _timer(self, kwargs):
    self._set()


#     if self.state == 'ON':
#       brightness = self.brightness
#       self.debug("Brightness {}", brightness)

#       now=self.datetime()
#       midnight=self.datetime().replace(hour=0,minute=0,second=0,microsecond=0)
#       seconds=(now-midnight).seconds
#       modulo=(seconds%(self.period*60))/10
#       self.debug("Seconds {}, period {}, modulo {}", seconds, self.period, modulo)

#     entities = enumerate(self.args["entities"])
#     l = len(self.args["entities"])
#     for i,entity in entities:
#       if self.state == 'ON':
#         hscolor=int((modulo+i*360/l)%360)
#         self.debug("Setting color for {} to {}", entity, hscolor)
#         self.turn_on(entity, hs_color=[hscolor,100], brightness=self.brightness)
#       elif self.state == 'OFF':
#         self.debug("Turning off")
#         self.turn_off(entity)
#       else:
#         self.debug("Unkown state {}".format(self.state))
    
#     status = {}
#     status['state']=self.state
#     if self.brightness:
#       status['brightness']=self.brightness
#     status_json = json.dumps(status)
#     if self.topic_state:
#       self.debug("Status Publish to Topic {} Payload {}", self.topic_state, status_json)
#       self.call_service("mqtt/publish", topic=self.topic_state, payload=status_json)
#     else:
#       self.debug("No state topic")    

  # def _update(self):
  #   if self.state == 'ON':
  #     brightness = self.brightness
  #     self.debug("Brightness {}", brightness)

  #     now=self.datetime()
  #     midnight=self.datetime().replace(hour=0,minute=0,second=0,microsecond=0)
  #     seconds=(now-midnight).seconds
  #     modulo=(seconds%(self.period*60))/10
  #     self.debug("Seconds {}, period {}, modulo {}", seconds, self.period, modulo)

  #   entities = enumerate(self.args["entities"])
  #   l = len(self.args["entities"])
  #   for i,entity in entities:
  #     if self.state == 'ON':
  #       hscolor=int((modulo+i*360/l)%360)
  #       self.debug("Setting color for {} to {}", entity, hscolor)
  #       self.turn_on(entity, hs_color=[hscolor,100], brightness=self.brightness)
  #     elif self.state == 'OFF':
  #       self.debug("Turning off")
  #       self.turn_off(entity)
  #     else:
  #       self.debug("Unkown state {}".format(self.state))
    
  #   status = {}
  #   status['state']=self.state
  #   if self.brightness:
  #     status['brightness']=self.brightness
  #   status_json = json.dumps(status)
  #   if self.topic_state:
  #     self.debug("Status Publish to Topic {} Payload {}", self.topic_state, status_json)
  #     self.call_service("mqtt/publish", topic=self.topic_state, payload=status_json)
  #   else:
  #     self.debug("No state topic")

# class colorloop(unibridge.AppHass):
#   def initialize(self):
#     self.state = 'OFF'
#     self.topic_state = None
#     self.topic_set = None
#     try: self.period = int(self.args["period"])
#     except: self.period = 60
#     try: self.precision = int(self.args["precision"])
#     except: self.precision = 5
#     try: self.brightness = int(self.args["brightness"])
#     except: self.brightness = 128

#     self.set_namespace(self.args["namespace"])
#     self.timer = self.run_every(self._timer, self.datetime(), self.precision)
  
#   def terminate(self):
#     self.cancel_timer(self.timer)
  
#   def _timer(self, kwargs):
#     self._update()

#   def light_on(self, brightness = 128):
#     self.state = 'ON'
#     self.brightness = brightness
#     self.debug("Switching on")
#     self._update()
#   def light_off(self):
#     self.state = 'OFF'
#     self.debug("Switching off")
#     self._update()

#   def _update(self):
#     if self.state == 'ON':
#       brightness = self.brightness
#       self.debug("Brightness {}", brightness)

#       now=self.datetime()
#       midnight=self.datetime().replace(hour=0,minute=0,second=0,microsecond=0)
#       seconds=(now-midnight).seconds
#       modulo=(seconds%(self.period*60))/10
#       self.debug("Seconds {}, period {}, modulo {}", seconds, self.period, modulo)

#     entities = enumerate(self.args["entities"])
#     l = len(self.args["entities"])
#     for i,entity in entities:
#       if self.state == 'ON':
#         hscolor=int((modulo+i*360/l)%360)
#         self.debug("Setting color for {} to {}", entity, hscolor)
#         self.turn_on(entity, hs_color=[hscolor,100], brightness=self.brightness)
#       elif self.state == 'OFF':
#         self.debug("Turning off")
#         self.turn_off(entity)
#       else:
#         self.debug("Unkown state {}".format(self.state))
    
#     status = {}
#     status['state']=self.state
#     if self.brightness:
#       status['brightness']=self.brightness
#     status_json = json.dumps(status)
#     if self.topic_state:
#       self.debug("Status Publish to Topic {} Payload {}", self.topic_state, status_json)
#       self.call_service("mqtt/publish", topic=self.topic_state, payload=status_json)
#     else:
#       self.debug("No state topic")