import yala
import life

OFF = 'off'
ON = 'on'
ENTITY_STATES = [ON, OFF]
TODS = ['d', 'e', 'n', 's']
TOD_STATES = [ON, 'motion', OFF]

# region Class Light
class Light(yala.Entity):
  __brightness = None
  __tods = None

  def __init__(self, d, env: life.Environment):
    super().__init__(d = d, env = env)
    tods = {}
    for t in TODS:
      tods[t] = {}
      states_raw = d.get(t, "50% none off")
      states = []
      states = states_raw.split()
      for i,S in enumerate(TOD_STATES):
        tods[t][S]=states[i]
    self.__tods = tods
  def __del__(self):
    super().__del__()

  @property
  def brightness(self):
    return __brightness
  @brightness.setter
  def brightness(self, brightness = 50):
    self.state('on', brightness = brightness)

  @property
  def state(self):
#    s = super().state
    # raw_state = self.get_hassio_state(entity_id = self.entity_id, namespace = 'deuce', attribute = 'all')
    # if isinstance(raw_state, dict):
    #   b = raw_state.get('attributes').get('brightness')
    # else:
    #   self.debug(f"Raw state from hassio {raw_state}")
    #   return None
    # if b:
    #   brightness = math.ceil(b/2.55)
    #   b = brightness
    # else:
    #   b = 0
    
    s = OFF
    b = 0

    __brightness = b
    __state = s
    return s, b
  @state.setter
  def state(self, state = None, brightness = 50):
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
  def __tod_action(self, action):
    a = self.__tods.get(self.tod).get(action)
    self.__debug(f"{self.__tods}")
    self.__debug(f"tod_action for {action} is {a}")
    return a
  @property
  def __str__(self):
    return f"{self.__name} is {self.__domain}.{self.__entity} @ {self.__namespace}\n    tods {self.__tods}"

  def __c_state(self, entity, attribute, old, new, **kwargs):
    b = attribute.get('brightness')
    b_pct = attribute.get('brightness_pct')
    if not b and not b_pct:
      super().__c_state(entity, attribute, old, new, kwargs)
      return
    try:
      if b_pct:
        brightness = int(b_pct)
      else:
        brightness = math.ceil(b/2.55)
    except:
      self.error(f"Impossible brightness x{b} or {b_pct}%")
      pass
    else:
      self.__state = new
      self.__brightness = b

  def action(self, action = None):
    current_tod = self.tod
    current_state = self.state
    to_state_raw = self.desired_state(action)
    to_state = None
    to_brightness = None
    if to_state_raw == OFF:
      to_state = OFF
    elif '%' in to_state_raw:
      to_state = ON
      to_brightness = to_state_raw.split('%')[0]

    self.debug(f"    Current tod: {current_tod}")
    self.debug(f"    Current state: {current_state}")
    self.debug(f"    Desired state: {to_state}")

    self.state(state = to_state, brightness = to_brightness)
# endregion

