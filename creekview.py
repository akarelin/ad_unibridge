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
from u3 import T_MQTT
SCHEMA_ACTION = {
    vol.Exclusive('transformer', 'action'):{vol.Required('transformer'): str}
  }
# endregion

class Creekview(u3.Universe):
  synonyms = {}
  keypads_isy = {}
  keypads_i2 = {}
  buttons_isy = {}
  areamap = {}

  def initialize(self):
    super().initialize()
    schema = {
        vol.Optional("i2_keypads"): dict,
        vol.Optional("isy_slugs"): dict
      }
    super().load(schema)
    self.LoadAreas()
    self.LoadKeypads()
    self.LoadEntities()
  def terminate(self): super().terminate()

  def LoadAreas(self): 
    am = self.p('areamap')
    for area,area_synonym in am.items():
      if isinstance(area_synonym, str): self.areamap[area] = area_synonym
      elif isinstance(area_synonym, dict):
        subsyn = {k: f"{area}/{v}" if v else f"{area}/{k}" for k,v in area_synonym.items()}
        for subarea,synonym in subsyn.items(): self.areamap[subarea] = synonym
  
  def LoadKeypads(self):
    keypads = self.p('keypads')
    for k in keypads:
      path = k.get('path')
      area = path.split('/')[0]
      tail = k.get('tail')
      if tail: self.keypads_isy[tail] = {'area': area, 'path': path, 'button_map': k.get('button_map')}
      else: self.keypads_i2[path] = {'area': area, 'buttons': k.get('buttons')}
    return

  def LoadEntities(self):
    for d in ['light','sensor']:
      for e in self.hass.get_state(d):
        entity = e.split('.')[1]
        eparts = []
        tail = None
        action = None
        area = None
        bm = {}
        if not isinstance(entity, str): continue
        if entity.endswith('_dimmer'): continue
        if not entity.startswith('btn_'): continue
        eparts = entity.split('_')
        eparts.pop(0)
        tail = eparts.pop(-1)
        if tail not in self.keypads_isy: continue
        keypad = self.keypads_isy.get(tail)
        action = '-'.join(eparts)
        bm = keypad.get('button_map')
        keypad_path = keypad.get('path')
        area = keypad_path.split('/')[0]
        if bm: action = bm.get(action, action)
        if '/' in action:
          area = action.split('/')[0]
          action = action.replace(f"{area}/", "")
        btn = {'area': area, 'action': action}
        self.buttons_isy[e] = btn
    return

class x2y(u3.U3):
  regex = None
  transformer = None
  trigger = None
  action_conditions = {}

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
    super().load({**schema_trigger, **SCHEMA_ACTION})
    # region Triggers  
    trigger = self.P('trigger')
    if trigger: self.trigger = trigger
    else: return
    event = trigger.get('event')
    topic = trigger.get('topic')
    entity = trigger.get('entity')
    singles_list = trigger.get('singles_list')
    if event: self.add_event_trigger({'event': event})
    elif topic:
      list = topic.get('list')
      operand = topic.get('operand')
      topics = []
      if list and operand and operand == 'keys': topics = self.universe.keypads_i2.keys()
      if topics:
        self.trigger_topics = topics
        head = trigger.get('head').split('/')
        tail = trigger.get('tail').split('/')
        for topic in topics: 
          tparts = topic.split('/')
          t = head + tparts + tail
          self.add_mqtt_trigger({'topic': '/'.join(t)})
    elif entity: self.add_state_trigger({'entity': entity})
    elif singles_list:
      list_info = self.U(singles_list)
      value_template  = list_info.get('value_template')
      domain = list_info.get('domain')
      conditions = list_info.get('conditions')
      action_template = list_info.get('action_template')
      if action_template and value_template and conditions and domain and isinstance(conditions, dict):
        for slug, condition in conditions.items():
          topic = self.hass.render_template(action_template.replace('SLUG',slug))
          if ' ' in condition: (entity, operand) = condition.split(' ', 1)
          if not entity.startswith(domain): entity = f"{domain}.{entity}"
          condition = value_template.replace('ENTITY', entity).replace('OPERAND', operand)
          self.action_conditions[entity] = {'condition': condition, 'action': topic}
          self.add_state_trigger({'entity': entity})
      self.transformer = 'Sensor2Topic'
      return
    action = self.P('action')
    if 'transformer' in action: self.transformer = action.get('transformer')
    else: self.Error(f"Invalid action {action}")

  # region Events. Used by ISY
  def cb_event(self, data):
    if data.get('event') == EVENT_ISY: self.ISYEvent(data)
  def ISYEvent(self, data):
    event, entity, control = data.pop('event'), data.pop('entity_id'), data.pop('control')
    if not entity: return
    if not control or control in IGNORE_ISY_EVENTS: return
    if control[0] == 'D': control = control[1:]
    data['control'] = control
    if entity: data['entity'] = entity
    if not control: return
    if self.transformer == 'ISY2Action': self.ISYAction(entity, data)
    elif self.transformer == 'ISY2Sensor':
      regex = self.P('trigger').get('regex')
      eparts = []
      entity = data.get('entity')
      if regex:
        try: eparts = re.findall(regex, entity)[0].split('_')
        except: return
        self.ISYSensor(eparts, data)
  # def ISYEventParser(self, data):
  #   control = data.get('control')
  #   if not control or control in IGNORE_ISY_EVENTS: return
  #   if control[0] == 'D': control = control[1:]
  #   event, entity = data.pop('event'), data.pop('entity_id')
  #   if event != EVENT_ISY: return
  #   if entity: data['entity'] = entity
  #   return data
  def ISYAction(self, entity, data):
    btn = self.universe.buttons_isy.get(entity)
    if not btn: 
      self.Error(f"ISY Action {entity}, {data}")
      return
    area = btn.get('area')
    action = btn.get('action')
    path = btn.get('path')
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
  # endregion
  # region MQTT. Used by I2
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
      actions = self.universe.keypads_i2.get(path).get('buttons')
      if not actions: actions = self.universe.keypads_i2.get(topic).get('buttons')
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
  # region 
  # region State. Used for power sensing and new style indicatior-actions
  def cb_state(self, entity, attribute, old, new, kwargs):
    if self.transformer == 'Attribute2Sensor': self.Attribute2Sensor(entity, new)
    elif self.transformer == 'Sensor2Topic': self.Sensor2Topic(entity, new)
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
        try: self.mqtt.mqtt_publish(topic, float(a))
        except: continue
        else: return
  def Sensor2Topic(self, entity, state):
    ac = self.action_conditions.get(entity)
    condition = ac.get('condition')
    action = ac.get('action')
    if condition and action and state:
      try: control = self.hass.render_template(condition)
      except: return
      self.mqtt.mqtt_publish(action, control)
      


      
      





  # endregion

class Indicator(u3.U3):
  transformer = None

  def initialize(self):
    super().initialize()
    super().load(SCHEMA_ACTION)
    action = self.P('action')
    self.transformer = action.get('transformer')
    if self.transformer not in ['Indicator2Switch']: self.Error(f"Invalid action {action}")
  def cb_mqtt(self, data):
    topic = data.get('topic')
    payload = data.get('payload').lower()
    if self.transformer == 'Indicator2Switch':
      self.Indicator2Switch(data)
  def Indicator2Switch(self, data):
    entity = f"switch.{topic.replace('/','_')}"
    if payload in ['on','off']: self.hass.call_service(f"homeassistant/turn_{payload}", entity_id = entity)

