import life
import light
import voluptuous as vol
from yala import MqttEntity, HassioEntity

import appdaemon.adbase as ad
import appdaemon.adapi as adapi

# region Ideas
"""
ao_bathroom_ceiling:
  module: simpleton
  name: ceiling
  room: ao_bathroom

  lights:
    - light.ao_bathroom_ceiling:
      name: ceiling
      namespace: deuce
      # triplets of on, motion, off
      d:  75%   50%   off
      e:  50%   33%   off
      n:  50%   33%   off
      s:  50%   none  off
  interlock:
    - light.dimmer_ao_bathroom_ceiling:
      name: dimmer
      namespace: deuce
      type: isy
"""

"""
ao_bathroom_vanity:
  module: simpleton
  name: vanity
  room: ao_bathroom

  lights:
    - light.ao_bathroom_vanity:
      name: ceiling
      namespace: deuce
      # triplets of on, motion, off
      d:  75%   50%   off
      e:  50%   33%   off
      n:  50%   33%   off
      s:  33%   20%   off
"""

"""
ao_bathroom.fanlight:
  module: simpleton
  name: fanlight

  devices:
    - switch.ao_bathroom_fanlight:
      name: fan
      namespace: deuce
      # triplets of on, motion, off
      d:  on   none   off
      e:  on   none   off
      n:  on   none   off
      s:  on   none   off
  timeout:
    off:  1h
    no_motion: 1h
    disabled: 2h
"""

"""
ao_bathroom.sensors:
  module: sensors
  name: ao_bathroom

  sensors:
    - binary_sensor.ao_bathroom_s1: 
        name: s1
        attributes: [lux, temp]
    - binary_sensor.ao_bathroom_s2:
        name: s2
        attributes: [lux, temp]
    - binary_sensor.ao_bathroom_occupancy:
        name: ecobee
        attributes: [temp, hum]

  motion:
    members: [s1, s2]
    timeout: 60s
  presence:
    members: [s1, s2]
    timeout: 5m
  absense:
    members: [s1, s2, ecobee]
    timeout: 30m
"""


"""
ao_bathroom:
  module: room
  name: ao_bathroom
  
  members:
    - vanity
    - ceiling
    - nightlight
    - fanlight
    - sensors

  indicators:
    - switch.ind_ao_bathroom_anyon
"""
# endregion

# region Class Simpleton
OFF = 'off'
ON = 'on'
SWITCH_STATES = [ON, OFF]
SWITCH = 'switch'

class Simpleton(life.Organizm, yala.MqttEntity):
# region Example
  """
  ao_bathroom_ceiling:
    module: simpleton
    name: ceiling
    room: ao_bathroom

    devices:
      - light.ao_bathroom_ceiling:
        name: ceiling
        namespace: deuce
        type: isy
        # triplets of on, motion, off
        d:  75%   50%   off
        e:  50%   33%   off
        n:  50%   33%   off
        s:  50%   none  off
    interlock:
      - light.dimmer_ao_bathroom_ceiling:
        entity: light.dimmer_ao_bathroom_ceiling
        name: dimmer
        namespace: deuce
        type: isy
  """
# endregion
# region Constructor/Destructor
  name = None
  room = None

  __state = None
  __brightness = None
  handles = []
  __force_refresh_interval = "1h"
  __refresh_interval = "1m"
  members = []

  def initialize(self):
    self.__initialize()
  def terminate(self):
    pass

  def __initialize(self):
    # Simpleton
    self.name = self.args.get('name')
    if not self.name:
      self.error("No name!")
      return
    self.room = self.args.get('room')
    # devices
    devices = self.args.get('devices')
    if devices:
      for d in devices:
        m = light.Light(d, env = self)
        # self.debug(f"Member: {m}")
        self.members.append(m)
    # MQTT
    e = self.args.get('entity_id', f"switch.{self.__name__}")

    super(life.Organizm).initialize()
    super(yala.MqttEntity).__init__(env = self, entity_id = e)

  def refresh(self, force = False):
    for m in self.members:
      m.refresh(force)
    self.__publish()

  @property
  def state(self):
    state = None
    brightness = 0.0
    brightnesses = []
    for m in self.members:
      state = m.state 
      if state:
        s, b = state
        if s == 'on':
          if b > 0:
            brightnesses.append(b)
          self.__state = 'on'
        elif s == 'off':
          self.__state = 'off'
    if brightnesses:
      self.__brightness = sum(brightnesses)
    self.__publish()
    return self.__state, self.__brightness

  def action(self, action):
    self.__debug(f"Action {action}")
    for m in self.members:
      m.set_state(action)
    self.__publish()



# endregion

# endregion
  # interlocks = []
  # def __c_interlock(self, entity = None, **kwargs):
  #   __interlocks = []
  #   for i in interlocks:
  #     if entity and i['entity'] != entity:
  #       continue
  #     e = i['entity']
  #     n = i['name']
  #     namespace = i['namespace']
  #     t = i['type']
  #     state_raw = self.api.get_state(entity_id = e, namespace = namespace )
  #     state = s.get(e).get('state')
  #     if state != self.state:
  #       if self.state == 'on':
  #         self.api.call_service("homeassitant/turn_on", entity_id = e, namespace = n)
  #       elif self.state == 'off':
  #         self.api.call_service("homeassitant/turn_off", entity_id = e, namespace = n)
