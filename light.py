#import appdaemon.plugins.hass.hassapi as hass
import unibridge
import json
from datetime import datetime, time
from typing import Any, Dict, List, Optional, Set, Union

"""
bedroom_ambient:
  module: light
  class: group
  dependencies:
    - mqtt
  namespace: sway_hassio

  name: "Bedroom Lamps"
  topic: 'bedroom/ambient'

  effect: None
  rgb_color: [255,116,22]

  members:
    - light.hue_bedroom_1 @ sway_hassio
    - light.hue_bedroom_2 @ sway_hassio
    - light.hue_bedroom_3 @ sway_hassio
  
  indicators:
    - 'insteon/kp/wall/state/1' @ sway_mqtt
    - 'insteon/kp/desk/state/1' @ sway_mqtt
  definitive_state:
    - light.hue_bedroom @ sway_hassio
  control_indicators:
    - 'insteon/kp/wall/set/1' @ sway_mqtt
    - 'insteon/kp/desk/set/1' @ sway_mqtt
 
"""

class group(unibridge.AppHybrid):
  def initialize(self):
    super().initialize()
    self._load_config()
    self.debug("Members {}",self.members)
    self.debug("Definitive State {}",self.definitive_state)
    self.debug("Indicators {}",self.definitive_state)

  def _load_config(self):
    self.members = self._load_entity_list(self.args['members'])
    self.definitive_state = self._load_entity_list(self.args['definitive_state'])
    self.indicators = self._load_entity_list(self.args['indicators'])
  
  def _mqtt(self, event_name, data, kwargs):
    self.debug("Topic {} Payload {}", data['topic'], data['payload'])
  
  @staticmethod
  def _load_entity_list(arg):
    entity_list = []
    for m in arg:
      e = m.split(' @ ')[0]
      n = m.split(' @ ')[1]
      if 'mqtt' in n: t = 'MQTT'
      elif 'hass' in n: t = 'Hassio'
      else:
        self.error("Invalid member {}", m)
        return
      member = {}
      member['type'] = t
      member['namespace'] = n
      member['entity'] = e
      entity_list.append(member)
    return entity_list

  # def init(self):
  #   self.set_namespace(self.args["namespace"])
  #   self.entities = []
  #   self.entities = self.args["entities"]
  #   self.entity_count = len(self.args["entities"])

  #   try: self.brightness = int(self.args["brightness"])
  #   except: self.brightness = 128

  #   try: self.rgb_color = self.args["rgb_color"]
  #   except: self.rgb_color = None

  #   try: self.effect = self.args["effect"]
  #   except: self.effect = None
    
  #   if self.effect == 'colorloop':
  #     self.init_colorloop()
  
  # def init_colorloop(self):
  #   try: self.period = int(self.args["period"])
  #   except: self.period = 60
  #   try: self.precision = int(self.args["precision"])
  #   except: self.precision = 5
  #   self.timer = self.run_every(self._timer, self.datetime(), self.precision)

  # def light_on(self, brightness = 128):
  #   self.state = 'ON'
  #   self.brightness = brightness
  #   self.debug("Switching on")
  #   self._set()
  # def light_off(self):
  #   self.state = 'OFF'
  #   self.debug("Switching off")
  #   self._set()

  # def _set(self):
  #   self.debug("Setting entities {} effect {}",self.entities,self.effect)
  #   if self.effect == 'colorloop':
  #     self._set_colorloop()
  #   else:
  #     self._set_color()
  #   self._publish()
  
  # def _set_color(self):
  #   self.debug("Setting entities {}, brightness {}, color",self.entities,self.brightness,self.rgb_color)
  #   for i,entity in enumerate(self.entities):
  #     if self.state == 'ON':
  #       self.debug("Turning on entity {}, brightness {}, color",entity,self.brightness,self.rgb_color)
  #       self.turn_on(entity, rgb_color=self.rgb_color, brightness=self.brightness)
  #     elif self.state == 'OFF':
  #       self.debug("Turning off entity {}",entity)
  #       self.turn_off(entity)
  #     else:
  #       self.debug("Unkown state {}".format(self.state))
   
  # def _set_colorloop(self):
  #   now=self.datetime()
  #   seconds=(now-self.datetime().replace(hour=0,minute=0,second=0,microsecond=0)).seconds
  #   modulo=(seconds%(self.period*60))/10

  #   e = enumerate(self.entities)
  #   for i,entity in enumerate(self.entities):
  #     if self.state == 'ON':
  #       hscolor=int((modulo+i*360/self.entity_count)%360)
  #       self.turn_on(entity, hs_color=[hscolor,100], brightness=self.brightness)
  #     elif self.state == 'OFF':
  #       self.turn_off(entity)
  #     else:
  #       self.error("Unkown state {}".format(self.state))

  # def _publish(self):
  #   status = {}
  #   status['state']=self.state
  #   if self.state == 'ON':
  #     if self.brightness:
  #       status['brightness']=self.brightness
  #     if self.rgb_color:
  #       status['rgb_color']=self.rgb_color
  #   status_json = json.dumps(status)
  #   if self.topic_state:
  #     self.debug("Status Publish to Topic {} Payload {}", self.topic_state, status_json)
  #     self.call_service("mqtt/publish", topic=self.topic_state, payload=status_json)
  #   else:
  #     self.debug("No status topic")

  # def _timer(self, kwargs):
  #   self._set()
