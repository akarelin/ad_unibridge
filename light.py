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
# Bitfield of features supported by the light entity
SUPPORT_BRIGHTNESS = 1
SUPPORT_COLOR_TEMP = 2
SUPPORT_EFFECT = 4
SUPPORT_FLASH = 8
SUPPORT_COLOR = 16
SUPPORT_TRANSITION = 32
SUPPORT_WHITE_VALUE = 128

# Integer that represents transition time in seconds to make change.
ATTR_TRANSITION = "transition"

# Lists holding color values
ATTR_RGB_COLOR = "rgb_color"
ATTR_XY_COLOR = "xy_color"
ATTR_HS_COLOR = "hs_color"
ATTR_COLOR_TEMP = "color_temp"
ATTR_KELVIN = "kelvin"
ATTR_MIN_MIREDS = "min_mireds"
ATTR_MAX_MIREDS = "max_mireds"
ATTR_COLOR_NAME = "color_name"
ATTR_WHITE_VALUE = "white_value"

# Brightness of the light, 0..255 or percentage
ATTR_BRIGHTNESS = "brightness"
ATTR_BRIGHTNESS_PCT = "brightness_pct"

# String representing a profile (built-in ones or external defined).
ATTR_PROFILE = "profile"

# If the light should flash, can be FLASH_SHORT or FLASH_LONG.
ATTR_FLASH = "flash"
FLASH_SHORT = "short"
FLASH_LONG = "long"

# List of possible effects
ATTR_EFFECT_LIST = "effect_list"

# Apply an effect to the light, can be EFFECT_COLORLOOP.
ATTR_EFFECT = "effect"
EFFECT_COLORLOOP = "colorloop"
EFFECT_RANDOM = "random"
EFFECT_WHITE = "white"

"""
|||||||||||||||||||||||||||||
Adhocs
|||||||||||||||||||||||||||||
"""
# Light Types
TYPE_HASS = "HASS"
TYPE_MQTT = "MQTT"
# Light States
STATE_ON = "ON"
STATE_OFF = "OFF"
STATE_UNKNOWN = None
LIGHT_STATES = [STATE_ON, STATE_OFF, STATE_UNKNOWN]
# Ignoder Attributes
IGNORE_STATES = [
  'context'
]
IGNORE_ATTRIBUTES = [
  'custom_ui_state_card',
  'state_card_mode',
  'stretch_slider',
  'effect_list',
  'effect',
  'supported_features',
  'hs_color',
  'xy_color',
  'max_mireds',
  'min_mireds'
]
CONVERT_ATTRIBUTES = [
  'brightness',
  'rgb_color'
]

class groupMember:
  type = None
  state = None
  entity_id = None

  hass = None
  hass_state = None

  def __init__(self, cfg, hass):
    e = cfg.split(' @ ')[0].lower()
    n = cfg.split(' @ ')[1].lower()
    if TYPE_MQTT.lower() in n: t = TYPE_MQTT
    elif TYPE_HASS.lower() in n: t = TYPE_HASS
    else:
      self.error("Invalid member {}", cfg)
      return
    
    self.type = t
    self.namespace = n
    self.entity_id = e
    self.hass = hass
  
  def __repr__(self):
    return "{} @ {}".format(self.entity_id,self.namespace)
  
  def __str__(self):
    return "{} in {} => {}".format(self.entity_id,self.state)
  
  def stateFromHASS(self):
    state = self.hass.get_state(self.entity_id, attribute="all")
    if not state:
      self.hass.warn("Entity {} not found", self.entity_id)
      self.type = None
      return
#    self.hass.debug("Full state {}", state)
#    self.hass.debug("Attributes {}", state['attributes'])

    for s in IGNORE_STATES:
      if s in state: del state[s]
    for a in CONVERT_ATTRIBUTES:
#      self.hass.debug("Converting attributes of {}", state['attributes'])
      if a in state['attributes']:
        state[a] = state['attributes'][a]
        del state['attributes'][a]
    for a in IGNORE_ATTRIBUTES:
      if a in state['attributes']: del state['attributes'][a]
    self.hass_state = state
    self.state = state['state']

class group(unibridge.AppHybrid):
  @property
  def is_on(self):
    return self._state
  
  @property
  def brightness(self):
    return self._brightness

#  members = List[groupMember]
  members = []
  """
  State (Local) and Hassio State
  """
  # _state = {}
  # _state_hassio = {}
  # _state_desired = {}

  def update(self):
    for m in self.members:
      if m.type == TYPE_HASS:
        m.stateFromHASS()

  def initialize(self):
    super().initialize()
    self._load_config()
    self.update()
    self.debug("~~~ Current state {}", self.members)
  
  def _mqtt(self, event_name, data, kwargs):
    return
    self.debug("Topic {} Payload {}", data['topic'], data['payload'])

  """
  Loading
  """
  def _load_config(self):
    for a in self.args['members']:
      self.members.append(groupMember(a,self))
    
  #   self.members = self._load_entity_list(self.args['members'])
  #   self.definitive_state = self._load_entity_list(self.args['definitive_state'])
  #   self.indicators = self._load_entity_list(self.args['indicators'])

  # def _load_entity_list(self, arg):
  #   for a in arg:
  #     m = groupMember(a)

  #     entity_list.append(member)
  #   return entity_list

  """
  State Calculation
  """
  def _state_sum(self, state_array = []):
    result = {}
    result['state'] = STATE_UNKNOWN

    state = STATE_UNKNOWN
    brightness = None
    rgb_color = None

    v_b = []
    r_sum = 0
    g_sum = 0
    b_sum = 0
    rgb_count = 0

    for i,s in enumerate(self.state_array):
      if s['state'] == STATE_ON:
        state = STATE_ON

        try: v_b.append(int(s['brightness']))
        except:
          pass
        
        try:
          rgb = s['rgb_color']
          r = int(rgb[0])
          g = int(rgb[1])
          b = int(rgb[2])
        except:
          pass
        else:
          r_sum += r
          g_sum += g
          b_sum += b

      elif s['state'] == STATE_OFF:
        if s == STATE_UNKNOWN: s == STATE_OFF

    result['state'] = state

    if len(v_b) > 0:
      brightness = round(sum(v_b)/len(v_b))
      result['brightness'] = brightness
    
    if rgb_count > 0:
      r = r_sum/rgb_count
      g = g_sum/rgb_count
      b = b_sum/rgb_count
      rgb_color = (r,g,b)
      result['rgb_color'] = rgb_color
    
    return result

  # def _state_from_hassio(self):
  #   results = []
  #   for i,member in enumerate(self.members):
  #     if member['type'] == TYPE_HASS:
  #       state = self.get_state(member['entity'], attribute="all")
  #       if not state:
  #         self.warn("Entity {} not found",member['entity'])
  #         continue
  #       attributes = state['attributes']
  #       for s in IGNORE_STATES:
  #         if s in state: del state[s]
  #       for a in CONVERT_ATTRIBUTES:
  #         if a in attributes:
  #           state[a] = attributes[a]
  #           del attributes[a]
  #       for a in IGNORE_ATTRIBUTES:
  #         if a in attributes: del attributes[a]

  #       results[i] = state
  #       results[i]['attributes'] = attributes
    
  #   return results

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