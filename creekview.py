# region Imports and constants
import u3
import hassapi as hass
import pprint
import json
import inspect
import re
from collections import ChainMap, Iterable
import voluptuous as vol
from typing import Any, Callable, Dict, List, Optional, cast

MQTT = "trace_mqtt"
PREFIX_BUTTON = 'btn'
PREFIX_INDICATOR = 'ind'
PREFIX_ACTION = 'act'
EVENT_ACTION = 'ACTION'
EVENT_ISY = 'isy994_control'
PREFIX_SENSOR = 'sensor'
PREFIX_POWER = 'power'
IGNORE_KPARTS: List = ['kp','insteon','state']
IGNORE_ISY_EVENTS: List = ['RR','OR','ST']
MAX_EVENT_AGE = 10
IND_TYPE_I2 = 'i2'
IND_TYPE_INSTEON = 'insteon'
# endregion

class Creekview(u3.Universe):
  synonyms = {}
  isy_actions = {}
  i2_actions = {}

  def initialize(self):
    super().initialize()
    schema = {
        vol.Optional("i2_keypads"): dict,
        vol.Optional("isy_slugs"): dict
      }
    super().load(schema)
    self.LoadKeypads()
  def terminate(self): super().terminate()

  def LoadKeypads(self):
    i2 = {v.lower(): k for k,v in self._lower('i2_keypad_synonyms').items()}
    isy = {v.lower(): k for k,v in self._lower('isy_keypad_synonyms').items()}
    
    for keypad,actions in self._lower('keypad_actions').items():
      # actions = [a for a in actions if a]
      slug = isy.get(keypad)
      if slug: 
        for a in [a for a in actions if a]:
          entity_id = f"btn_{a.replace('-','_').lower()}_{slug}"
          self.isy_actions[entity_id] = a
        continue
      else:
        self.i2_actions[keypad] = actions
        synonym = i2.get(keypad)
        if synonym: self.i2_actions[synonym] = actions
    return

class x2y(u3.U3):
  regex = None
  transformer = None
  trigger = None

  def initialize(self):
    super().initialize()
    schema_trigger = {
      vol.Exclusive('event', "trigger"):{
        vol.Required("event"): str,
        vol.Required("regex"): str},
      vol.Exclusive("mapping", "trigger"):{
        vol.Required("mapping"): str},
      vol.Exclusive("state", "trigger"):{
        vol.Required("state"): str,
      }}
    schema_action = {
      vol.Exclusive('transformer', 'action'):{vol.Required('transformer'): str}
      }
    super().load({**schema_trigger, **schema_action})
    # region Triggers  
    trigger = self.P('trigger')
    if trigger: self.trigger = trigger
    event = trigger.get('event')
    topic = trigger.get('topic')
    entity = trigger.get('entity')
    if event: self.add_event_trigger({'event': event})
    elif topic:
      list = topic.get('list')
      operand = topic.get('operand')
      topics = []
      if list and operand and operand == 'keys':
        try: topics = self.U(list).keys()
        except: self.Error(f"Invalid mapping {topic} got {self.U(list)}")
      if topics:
        self.trigger_topics = topics
        head = trigger.get('head').split('/')
        tail = trigger.get('tail').split('/')
        for topic in topics: 
          tparts = topic.split('/')
          t = head + tparts + tail
          self.add_mqtt_trigger({'topic': '/'.join(t)})
    elif entity: self.add_state_trigger({'entity': entity})
    # endregion
    # region Actions
    action = self.P('action')
    self.transformer = action.get('transformer')
    if not self.transformer: self.Error(f"Invalid action {action}")
    # endregion

  # region Events. Used by ISY
  def cb_event(self, data):
    event, entity, control = data.pop('event'), data.pop('entity_id'), data.pop('control')
    if event != EVENT_ISY: return
    if not entity: return
    if not control or control in IGNORE_ISY_EVENTS: return
    if control[0] == 'D': control = control[1:]
    data['control'] = control
    if entity: data['entity'] = entity
    if not control: return
    if entity.split('.')[1].startswith('btn_'):
      if self.transformer == 'ISY2Action': self.ISYAction(entity, data)
    elif self.transformer == 'ISY2Sensor':
      regex = self.P('trigger').get('regex')
      eparts = []
      entity = data.get('entity')
      if regex:
        try: eparts = re.findall(regex, entity)[0].split('_')
        except: return
        self.ISYSensor(eparts, data)
  def ISYAction(self, entity, data):
    if '.' in entity: entity = entity.split('.')[1]
    eparts = entity.split('_')
    tail = eparts[-1]
    path = self.U('isy_keypad_synonyms').get(tail)
    tparts = path.split('/')
    area = tparts[0]
    action = self.universe.isy_actions.get(entity)
    control = data.get('control')
    self.api.fire_event(EVENT_ACTION, area = area, action = action, path = path, control = control)
    t = '/'.join([PREFIX_ACTION,area,action])
    self.mqtt.mqtt_publish(t, control)

  def ISYSensor(self, eparts, data):
    if 'btn' in eparts: return
    entails = self.U('isy_entity_tails')
    controls = self.U('isy_sensor_controls')
    tail = eparts.pop()
    if tail not in ['s','sensor']:
      if tail in ['s1','s2']: tail = tail[1]
      eparts.append(tail)
    control = data.pop('control')
    raw_value = data.pop('value')
    extras = data
    cp = controls.get(control)
    value = None
    if not cp:
      self.Error(f"Unknown control {control} or its parameters {controls}")
      return
    value_type = cp.get('type','str')
    try: 
      if value_type == 'float': v = float(raw_value)
      elif value_type == 'int': v = int(raw_value)
      else: v = raw_value
      if value_type == 'float': v = v*float(cp.get('value_multiplier'))
      elif value_type == 'int': v = int(v*float(cp.get('value_multiplier')))
    except:
      self.Warning(f"Invalid value {raw_value}")
      return
    tail = cp.get('tail')
    if tail in eparts: eparts.remove(tail)
    eparts.append(tail)
    topic = '/'.join([PREFIX_SENSOR]+eparts)
    self.mqtt.mqtt_publish(topic, value)
  def ISYEventParser(self, data):
    control = data.get('control')
    if not control or control in IGNORE_ISY_EVENTS: return
    if control[0] == 'D': control = control[1:]
    event, entity = data.pop('event'), data.pop('entity_id')
    if event != EVENT_ISY: return
    if entity: data['entity'] = entity
    return data
  # endregion
  # region MQTT. Used by I2.
  def cb_mqtt(self, data):
    topic = data.get('topic')
    payload = data.get('payload')
    if self.transformer == 'I2Action': self.I2Action(topic, payload)
  def I2Action(self, topic, payload):
    control = self.I2PayloadParser(payload)
    if control: 
      area,action = self.I2TopicParser(topic)
      if not action: return
      self.api.fire_event(EVENT_ACTION, area = area, action = action, control = control)
      self.mqtt.mqtt_publish(f"{PREFIX_ACTION}/{area}/{action}", control)
  def I2TopicParser(self, topic) -> (str,str):
    action = None
    head = self.trigger.get('head')
    topic = topic.replace(head, '')
    if topic[0] == '/': topic=topic[1:]
    tparts = [t for t in topic.split('/') if t not in IGNORE_KPARTS]
    area = tparts[0]
    if tparts[-1] in "12345678":
      button = int(tparts.pop(-1))
      path = '/'.join(tparts)
      actions = self.universe.i2_actions.get(path)
      if not actions: actions = self.universe.i2_actions.get(topic)
      if actions: action = actions[button-1]
    return (area,action)
  def I2PayloadParser(self, payload) -> str:
    p = {}
    try:
      p = json.loads(payload)
      reason = p.get('reason')
      ts = p.get('timestamp')
    except: return
    # if ts:
    #   delta = self.api.get_now_ts() - ts
    #   if delta > MAX_EVENT_AGE: return
    if reason not in ['device']: return
    return 'F' if p.get('mode').upper() in ['FAST'] else "" + p.get('state')[:2].upper()
  # endregion
  # region State. Used for power sensing
  def cb_state(self, entity, attribute, old, new, kwargs):
    if self.transformer == 'Attribute2Sensor': self.Attribute2Sensor(entity, new)
  def Attribute2Sensor(self, entity, state):
    action = self.P('action')
    action_attrs = action.get('attributes')
    attrs = state.get('attributes')
    dt = action.get('device_type')
    eparts = []
    eparts = entity.split('.')[1].split('_')

    if dt == 'power':
      if 'power' in eparts: eparts.remove('power')
      topic = '/'.join([PREFIX_POWER]+eparts)
      for a in [attrs.get(a) for a in attrs if a in action_attrs]:
        try:
          self.mqtt.mqtt_publish(topic, float(a))
          return
        except: continue
    # endregion