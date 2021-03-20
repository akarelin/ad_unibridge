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
INTERLOCK_PARAMETERS = ['entity', 'name', 'namespace', 'type']
# endregion

# region Class entity
class Entity:
# region constructor
  __entity = None
  __namespace = None
  __name = None
  __domain = None
  __e = None
  __h = None
  __state = None

  def __init__(self, d, env: unibridge2.Environment):
    name = None
    domain = None
    entity = None
    self.__e = env
    namespace = d.get('namespace', self.__e.default_namespace)
    self.__h = self.__e.get_plugin_api(namespace)
    _entity_id = None
    _entity_id = next(iter(d))
    if not _entity_id:
      self.__error(f"Device: {d} Error: Not an entity")
      return
    try:
      domain, entity = _entity_id.split('.')
    except:
      self.__error(f"Error: Invalid entity {_entity_id} for device {d}")
      return
    name = d.get('name')
    if not name:
      self.__error(f"Error: No name for device {d}")
      return
    self.__debug(f"{name} @ {namespace} ==> {domain} ==> {entity}")

    self.__entity = entity
    self.__namespace = namespace
    self.__domain = domain
    self.__name = name

# endregion
# region helpers
  def hassio_state(self, entity_id = None, namespace = None):
    if not entity_id:
      entity_id = self.entity_id
    if not namespace:
      namespace = self.__namespace
    return self.__e.api.get_state(entity_id = entity_id, namespace = namespace)
  def hassio_service(self, service, **kwargs):
    self.__e.api(f"homeassistant/{service}", entity_id = self.entity_id, namespace = self.__namespace, kwargs = kwargs)
  @property
  def entity_id(self):
    return '.'.join([self.__domain, self.__entity])
  @property
  def entity(self):
    return self.__entity
  @property
  def namespace(self):
    return self.__namespace
  @property
  def name(self):
    return self.__name
  @property
  def domain(self):
    return self.__domain
# endregion    
# base methods
  def refresh(self, force = False):
    if force:
      self.hassio("update_entity")
    s, b = self.state
  @property
  def state(self):
    raw_state = self.hassio_state()
    s = raw_state.get('state')
    __state = s
    return s
  @state.setter
  def state(self, state):
    if state in ['on', 'off']:
      self.hassio(f"turn_{state}")
# endregion
  # region private parts
  @property
  def __str__(self):
    return f"{self.__name} is {self.__domain}.{self.__entity} @ {self.__namespace}\n    tods {self.__tods}"
  def __tod_action(self, action):
    a = self.__tods.get(self.tod).get(action)
    self.__debug(f"{self.__tods}")
    self.__debug(f"tod_action for {action} is {a}")
    return a

  def __debug(self, msg):
    self.__e.debug(msg)
  def __error(self, msg):
    self.__e.error(msg)
  # endregion

# endregion
# region Class Light
class Light(Entity):
  __brightness = None
  __tods = None

  def __init__(self, d, env: unibridge2.Environment):
    super().__init__(d = d, env = env)
    tods = {}
    for t in TODS:
      tods[t] = {}
      states_raw = d.get(t, "50% none off")
      states = []
      states = states_raw.split()
      for i,S in enumerate(STATES):
        tods[t][S]=states[i]
    self.__tods = tods

  @property
  def brightness(self):
    return __brightness
  @brightness.setter
  def brightness(self, brightness = 50):
    self.state('on', brightness = brightness)

  @property
  def state(self):
    s = super().state
    raw_state = self.hassio_state(namespace = 'deuce', attribute = 'all')
    b = raw_state.get('attributes').get('brightness')
    if b:
      brightness = math.ceil(b/2.55)
      b = brightness
    else:
      b = 0
    __brightness = b
    __state = s
    return tuple(s, b)
  @state.setter
  def state(self, state = None, brightness = 50):
    self.hassio()
    if state == 'off':
      super().state(entity_id = self.entity_id, state = 'off')
    elif state == 'on':
      self.hassio("turn_on", brightness_pct = brightness)
  @property
  def tod(self):
    time = self.hassio_state(entity_id = 'sensor.time', namespace = 'deuce')
    if time == 'Evening':
      return 'e'
    elif time == 'Night':
      return 'n'
    elif time == 'Sleep':
      return 's'
    else:
      return 'd'

  def action(self, action = None):
    current_tod = self.tod
    current_state = self.state
    to_state_raw = self.desired_state(action)
    to_state = None
    to_brightness = None
    if to_state_raw == 'off':
      to_state = 'off'
    elif '%' in to_state_raw:
      to_brightness = to_state_raw.split('%')[0]

    self.debug(f"    Current tod: {current_tod}")
    self.debug(f"    Current state: {current_state}")
    self.debug(f"    Desired state: {to_state}")

    self.state(state = to_state, brightness = to_brightness)
# endregion

# region Class Indicator
class Indicator(Entity):
  __indicate = None

  def __init__(self, entity, indicate: Entity, env: Unibridge2.Environment):
    super().__init__(d, env)
    self.__indicate = indicate

  def refresh(self, force = False):
    desired_state = self.__indicate.state
    state = self.state
    if state != desired_state:
      if state in ['on','off']:
        self.hassio_service(f"turn_{state}")
# endregion

# region Class Simpleton
class Simpleton(unibridge2.Organizm):
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

  interlocks = []
  def __c_interlock(self, entity = None, **kwargs):
    __interlocks = []
    for i in interlocks:
      if entity and i['entity'] != entity:
        continue
      e = i['entity']
      n = i['name']
      namespace = i['namespace']
      t = i['type']
      state_raw = self.api.get_state(entity_id = e, namespace = namespace )
      state = s.get(e).get('state')
      if state != self.state:
        if self.state == 'on':
          self.api.call_service("homeassitant/turn_on", entity_id = e, namespace = n)
        elif self.state == 'off':
          self.api.call_service("homeassitant/turn_off", entity_id = e, namespace = n)
  def desired_state(self, action = None):
    tod_action = self.tod_action(action)
    self.debug(f"Action: {action} TOD Action: {tod_action}")
    return tod_action

  def refresh(self, hard = False):
    super().refresh()
    for m in self.members:
      m.refresh(hard)
  @property
  def state(self):
    state = None
    brightness = 0.0
    brightnesses = []
    for m in self.members:
      s, b = m.state
      if s == 'on':
        if b > 0:
          brightnesses.append(b)
        state = 'on'
      elif s == 'off':
          state = 'off'
    if brightnesses:
      brightness = sum(brightnesses)
    return state, brightness
  @state.setter
  def state(self, action):
    self.__debug(f"Setting state for {action}")
    for m in self.members:
      m.state(action)
  # region Init/Construct
  name = None
  room = None
  __hard_refresh_interval = "1h"
  __refresh_interval = "1m"
  members = []
  def initialize(self):
    super().initialize()
    self.__initialize()

  def __initialize(self):
    # Simpleton
    self.name = self.args.get('name')
    if not self.name:
      self.error("No members!")
      return
    self.room = self.args.get('room')
    # devices
    devices = self.args.get('devices')
    if devices:
      for d in devices:
        m = entity(d, env = self)
        # self.debug(f"Member: {m}")
        self.members.append(m)
    # interlocks
    interlocks_raw = self.args.get('interlock')
    if interlocks_raw:
      for i in interlock_raw:
        try:
          interlock = dict([(k,v) for k,v in i.items() if k not in INTERLOCK_PARAMETERS])
        except:
          self.error(f"Invalid interlock {i}")
        else:
          self.interlocks.append(interlock)
    # callbacks
    for i in interlocks:
      self.api.listen_state(self.__c_interlock, entity = i['entity'], namespace = i['namespace'], duration = 30)
        
  # endregion
# endregion