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
PREFIX_SENSOR = 'sensor'
PREFIX_POWER = 'power'
IND_TYPE_I2 = 'i2'
IND_TYPE_INSTEON = 'insteon'
# endregion

class Creekview(u3.Universe):
  synonyms = {}
  buttons2actions = {}

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
    synonyms = {k: v.split('/') for k,v in self._lower('i2_keypad_synonyms').items()}
    keypads = self._lower('i2_keypads')
    for keypad,buttons in keypads.items():
      if len(buttons) == 8:
        self.buttons2actions[keypad] = buttons
        synonym = synonyms.get(keypad)
        if synonym: self.button2actions[synonym] = buttons
      else: self.Warn(f"Keypad {keypad}: len({buttons}) == {len(buttons)}")

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
    if self.transformer in ['ISY2Sensor','ISY2Action']:
      data = self.ISYEventParser(data)
      regex = self.P('trigger').get('regex')
      eparts = []
      entity = data.get('entity')
      try: eparts = re.findall(regex, entity)[0].split('_')
      except: return
      if self.transformer == 'ISY2Sensor': self.ISYSensor(eparts, data)
      elif self.transformer == 'ISY2Action': self.ISYButton(eparts, data)
  def ISYButton(self, eparts, data):
    # 2DO
    tail = eparts.pop()
    eparts.append(tail)
  def ISYSensor(self, eparts, data):
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
      if value_type == 'float':
        v = v*float(cp.get(value_multiplier))
      elif value_type == 'int':
        v = int(v*float(cp.get(value_multiplier)))
    except:
      self.Warning(f"Invalid value {raw_value}")
      return
    tail = cp.get('tail')
    if tail in eparts: eparts.remove(tail)
    eparts.append(tail)
    topic = '/'.join([PREFIX_SENSOR]+eparts)
    self.mqtt.mqtt_publish(topic, value)
  def ISYEventParser(self, data):
    IGNORE: List = ['RR','OR','ST']
    event = data.pop('event')
    entity = data.pop('entity_id')
    if event not in ['isy994_control']: return
    if entity:
      control = data.pop('control')
      if control and control not in IGNORE:
        data['control'] = control
        data['entity'] = entity
        return data
  # endregion
  # region MQTT. Used by I2.
  def cb_mqtt(self, data):
    topic = data.get('topic')
    payload = data.get('payload')
    if self.transformer == 'I2Action':
      self.I2Action(topic, payload)
  def I2Action(self, topic, payload):
    control = self.I2PayloadParser(payload)
    if control: 
      t,action = self.I2TopicParser(topic)
      self.api.fire_event('ACTION', action = action, path = t, control = control)
      t = 'act/'+t
      self.mqtt.mqtt_publish(t, control)
  def I2TopicParser(self, topic) -> (str,str):
    action = None
    tparts = [t for t in topic.split('/') if t not in ['kp','insteon','state']]
    area = tparts[0]
    if tparts[-1] in ['1','2','3','4','5','6','7','8']:
      try: button = int(tparts.pop(-1))
      except: pass
      path = '/'.join(tparts)
      actions = self.universe.buttons2actions.get(topic)
      if actions: action = actions[button-1]
      return (path,action)
    else: return (topic, None)
  def I2PayloadParser(self, payload) -> str:
    p = {}
    try:
      p = json.loads(payload)
      reason = p.get('reason')
      ts = p.get('timestamp')
    except: return
    if ts:
      delta = self.api.get_now_ts() - ts
      if delta > 10: return
    if reason not in ['device']: return
    control = ('F' if p.get('mode').upper() in ['FAST'] else "") + p.get('state')[:2].upper()
    return control
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