import unibridge2
import json
import datetime

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

# region Constants
OFF = 'OFF'
ON = 'ON'
TODS = ['d', 'e', 'n', 's']
STATES = ['on', 'motion', 'off']
# endregion

class simpleton(unibridge2.Organizm):
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
  name = None
  room = None
  __members = []
  __tods = {}

# region Init/Construct
  def initialize(self):
    super().initialize()
    self.__init_members()

  def __init_members(self):
    self.name = self.args.get('name')
    if not name:
      self.error("No members!")
      return
    self.room = self.args.get('room')

    devices = self.args.get('devices')
    if devices:
      for d in devices:
        member = {}
        namespace = None
        name = None
        domain = None
        entity = None
        tods = {}

        name = l.get('name')
        if not name:
          self.error(f"Device: {d} Error: No name")
          return
        namespace = l.get('namespace',self.default_namespace)
        entity_id = l.get('entity')
        try:
          domain, entity = entity_id.split('.')
        except:
          self.error(f"Device: {d} Error: Invalid entity {entity_id}")
          return

        member['name'] = name
        member['domain'] = domain
        member['namespace'] = namespace
        member['entity'] = entity
        
        for t in TODS:
          states_raw = d.get(t, "50%\tnone\toff")
          states = []
          states = states_raw.split("\t")
          for i,s in enumerate(states):
            tods[TODS[i]] = s

        member['tods'] = tods
        
        self.debug(f"\tInit {self.room}.{self.name} => Adding member {member}")
        self.debug(f"\t\tTODs => {tods}")
        self.members.append(member)
# endregion
# endregion        
