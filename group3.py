import unibridge2
import json
import datetime
import pprint
import math

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
# region Constants
OFF = 'OFF'
ON = 'ON'
TODS = ['d', 'e', 'n', 's']
STATES = ['on', 'motion', 'off']
# endregion

# region member
class entity:
  __states = None
  __entity = None
  __namespace = None
  __name = None
  __domain = None
  __tods = {}
  __e = None
  __h = None

# region constructor
  def __init__(self, d, env: unibridge2.Environment):
    member = {}
    name = None
    domain = None
    entity = None
    self.__e = env
    namespace = d.get('namespace', self.__e.default_namespace)
    self.__h = self.__e.get_plugin_api(namespace)
    tods = {}
    _entity_id = None
    _entity_id = next(iter(d))
    if not _entity_id:
      self.__e.error(f"Device: {d} Error: Not an entity")
      return
    try:
      domain, entity = _entity_id.split('.')
    except:
      self.__e.error(f"Error: Invalid entity {_entity_id} for device {d}")
      return
    name = d.get('name')
    if not name:
      self.__e.error(f"Error: No name for device {d}")
      return
    self.__e.debug(f"{name} @ {namespace} ==> {domain} ==> {entity}")
    for t in TODS:
      tods[t] = {}
      states_raw = d.get(t, "50% none off")
      states = []
      states = states_raw.split()
      for i,S in enumerate(STATES):
        tods[t][S]=states[i]

    self.__entity = entity
    self.__namespace = namespace
    self.__domain = domain
    self.__name = name
    self.__tods = tods
# endregion
  
  @property
  def tod(self):
    time = self.__e.api.get_state(entity_id = 'sensor.time', namespace = 'deuce')
    if time == 'Evening':
      return 'e'
    elif time == 'Night':
      return 'n'
    elif time == 'Sleep':
      return 's'
    else:
      return 'd'

  def tod_action(self, action):
    a = self.__tods.get(self.tod).get(action)
    self.debug(f"{self.__tods}")
    self.debug(f"tod_action for {action} is {a}")
    return a
  @property
  def current_state(self):
    raw_state = self.__e.api.get_state(entity_id = self.entity_id, namespace = 'deuce', attribute = 'all')
    state = {}
    state['state'] = raw_state.get('state')
    a = raw_state.get('attributes')
    b = a.get('brightness')
    if b:
      brightness = math.ceil(b/2.55)
      state['brightness'] = brightness
    return state
  @property
  def entity_id(self):
    return '.'.join([self.__domain, self.__entity])

  def set_state(self, action = None):
    current_tod = self.tod
    current_state = self.current_state
    to_state = self.desired_state(action)

    self.debug(f"    Current tod: {current_tod}")
    self.debug(f"    Current state: {current_state}")
    self.debug(f"    Desired state: {to_state}")

    if to_state == 'off':
      self.__h.turn_off(self.entity_id)
    elif '%' in to_state:
      brightness = to_state.split('%')[0]
      self.__h.turn_on('.'.join([self.__domain, self.__entity]), brightness_pct = brightness)

  def debug(self, msg):
    self.__e.debug(msg)
  def error(self, msg):
    self.__e.error(msg)

  def desired_state(self, action = None):
    tod_action = self.tod_action(action)
    self.debug(f"Action: {action} TOD Action: {tod_action}")
    return tod_action
  def __str__(self):
    return f"{self.__name} is {self.__domain}.{self.__entity} @ {self.__namespace}\n    tods {self.__tods}"
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
  members = []

# region Init/Construct
  def initialize(self):
    super().initialize()
#    self.debug(f"Starting initialize: {self.args}")
    self.__init_members()
#    self.debug(f"Initialized: {self}")
#    self.debug(f"Default namespace: {self.default_namespace}")
#    tod=self.api.get_state(entity_id = 'sensor.time', namespace = 'deuce')
#    self.debug(f"Current time {tod}")
#    self.set_state('off')

  def set_state(self, action):
    self.debug(f"Setting state for {action}")
    for m in self.members:
      m.set_state(action)

  def __init_members(self):
    self.name = self.args.get('name')
    if not self.name:
      self.error("No members!")
      return
    self.room = self.args.get('room')

    devices = self.args.get('devices')
    if devices:
      for d in devices:
        m = entity(d, env = self)
        self.debug(f"Member: {m}")
        self.members.append(m)

  # def __str__(self):
  #   return f"{self.room} -> {self.name} -> {self.members}"
  # def __repr__(self):
  #   return __str__(self)