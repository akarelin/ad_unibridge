# region Imports and Constants
import u3
from u3 import MqttTopic
from u3_universe import U
import typing
from typing import List, Dict
import voluptuous as vol
import json
import datetime
import re
import pprint

MQTT = "trace_mqtt"
PREFIX_BUTTON = 'btn'
PREFIX_INDICATOR = 'ind'
PREFIX_SENSOR = 'sensor'
PREFIX_POWER = 'power'
IND_TYPE_I2 = 'i2'
IND_TYPE_INSTEON = 'insteon'
# endregion

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
        try: topics = U(list).keys()
        except: self.Error(f"Invalid mapping {topic} got {U(list)}")
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
  #  if data.get('event') in ['state_changed','appd_started','call_service']: return
    if data.get('event') not in ['isy994_control']: return
    if self.transformer in ['ISY2Sensor','ISY2Action']:
      data = isy_DataFromEvent(data, self.ignore_events)
      eparts = []
      entity = data.get('entity')
      try: eparts = re.findall(self.button_regex, entity)[0].split('_')
      except: return
      if eparts: self.ISYButton(eparts, data)
      # OR
      data = isy_DataFromEvent(data)
      self.ISYSensor(data)
  def ISYButton(self, eparts, data):
    tail = eparts.pop()
    eparts.append(tail)
  def ISYSensor(self, data):
    entity = data.get('entity')
    eparts = []
    try: eparts = re.findall(self.sensor_regex, entity)[0].split('_')
    except: return
    tail = eparts.pop()
    tail = tail[1] if tail in ['s1','s2'] else '' if tail in ['s','sensor'] else tail
    eparts.append(tail)
    extract = ['control','value','uom']
    d = {key: data[key] for key in extract}
    topic = '/'.join([PREFIX_SENSOR]+eparts)
    self.mqtt.mqtt_publish(topic, json.dumps(d))

  def isy_DataFromEvent(data):
    INSTEON: Dict = U('insteon')
    IGNORE_EVENTS: List = INSTEON.get('ignore_events')
    event = data.pop('event')
    entity = data.pop('entity_id')
    if event not in ['isy994_control']: return
    if entity:
      control = data.pop('control')
      if control and control not in ignore_events: 
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
  def I2TopicParser(self, topic) -> (str,str):
    action = None
    head = self.trigger.get('head').split('/')
    tail = self.trigger.get('tail').split('/')
    synonyms = self.universe.config.get('i2_keypad_synonyms')
    REJECT = head + tail + ['kp','state']
    tparts = [t for t in topic.split('/') if t not in REJECT]
    area = tparts[0]
    try: button = int(tparts.pop(-1))
    except: self.Error(f"Unable to parse topic {topic}")
    else:
      path = '/'.join(tparts)
      actions = self.universe.buttons2actions.get(path)
      if actions: action = actions[button]
    finally: return (path,action)
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
  def I2Action(self, topic, payload):
    t,action = self.I2TopicParser(topic)
    control = self.I2PayloadParser(payload)
    if control: self.api.fire_event('ACTION', action = action, path = t, control = control)
    t = 'act/'+t
    self.mqtt.mqtt_publish(t, control)
  # endregion
  # region State. Used for power sensing
  def cb_state(self, entity, attribute, old, new, kwargs):
    if self.transformer == 'Attribute2Sensor': self.Attribute2Sensor(entity, new)
  def Attribute2Sensor(self, entity, state):
    value = 0.0
    eparts = []
    eparts = entity.split('.')[1].split('_')
    action = self.P('action')
    dt = action.get('device_type')
    attributes = action.get('attributes')
    if dt == 'power':
      if 'power' in eparts: eparts.remove('power')
    if attributes:
      values = [a for a in state.get('attributes') if a in attributes]
      for v in values:
        try:
          value = float(v)
          topic = '/'.join([PREFIX_POWER]+eparts)
          self.mqtt.mqtt_publish(topic, value)
          return
        except: pass


    # attributes = {}
    # attributes = state.get('attributes')
    # for k,v in attributes.items():
    #   if k in self.sensor_attributes:
    #     try:
    #       value = float(v)
    #       topic = '/'.join([PREFIX_POWER]+eparts)
    #       self.mqtt.mqtt_publish(topic, value)
    #       return
    #     except: pass
  # endregion

# region Junk
  # def Action(self, data, type = 'event'):
  #   # area = data.get('area')
  #   # action = data.get('action')
  #   # control = data.get('control')
  #   # topic = data.get('topic')
  #   # payload = {'action': action, 'area': area, 'path': topic, 'control': control}
  #   p = { key: data[key] for key in ['area','action','control','topic'] }
  #   if type == 'event': self.api.fire_event('ACTION', p)
  #   elif type == 'mqtt': 
  #     tparts = ['act']
  #     if p.get('area'): tparts.append(p.get('area'))
  #     tparts.append(p.get('action'))
  #     self.mqtt.mqtt_publish('/'.join(tparts), p)

   # insteon/{keypad or device} =====> btn/{keypad}
  # Button is called from I2Entity
  # def Button(self, tparts, button, control):
  #   self.Debug(f"Button [{tparts}] -> [{button}]")
  #   topic = '/'.join(keypad, button)
  #   topics = self.buttonmap.get(topic)
  #   if topics: 
  #     for t in topics:
  #       self.mqtt.mqtt_publish(t, payload)

# class mqtt_i2(u3.U3):
#   def initialize(self):
#     super().initialize()
#     bconfig = self.args.get('button')
#     if bconfig: 
#       trigger = bconfig.get('trigger')
#       if trigger == 'event': 
#         type = bconfig.get('type')
#         if type == 'isy994_event': 
#           regex = bconfig.get('regex')
#           if regex:
#             self.button_regex = regex
#             self.add_event_trigger({'event': 'isy994_control'})
#           else: self.Error(f"Invalid Regex")
#         else: self.Error(f"Invalid Type")
#       elif trigger == 'mqtt':
#         type = bconfig.get('type')
#         if type == 'i2': 
#           for topic in self.u('keypad_topics'):
#             self.add_mqtt_trigger({'topic': topic})
#         else: self.Error(f"Invalid type")
#       else: self.Error(f"Invalid trigger")
#     else: self.Error(f"No button specified")


#     control = data.get('control').replace('D','')
#     if not control or control in self.ignore_events: 
#       self.Debug(f"Ignoring control {control}")
#       return
#     data['control'] = control

#     eparts = None
#     if self.button:
#       try:
#         eparts = re.findall(self.button['regex'], entity_id)[0].split('_')
#         slug = eparts.pop()
#         if slug in self.slugs: slug = self.slugs.get(slug)
#         eparts.append(slug)
#       except: pass
#       self.ISYButton(eparts, control)
#     elif self.sensor:
#       try:
#         eparts = re.findall(self.sensor['regex'], entity_id)[0].split('_')
#       except: pass
#       self.ISYSensor(eparts, data)

#   def ISYButton(self, eparts, control):
#     keypad = eparts.pop()
#     button = '_'.join(eparts)
#     self.Button(keypad, button, control)

#   # Processor for all MQTT topics from i1 and i2
#   def I2Button(self, topic, payload):
#     if payload.get('reason') not in ['device']: return
#     tparts = topic.split('/')
#     tparts.remove('state')
#     button = tparts.pop()
#     control = 'F' if payload['mode'] in ['fast'] else '' + payload['state'][:2].upper()
#     tparts.remove('kp')
#     tparts.remove('insteon')
#     self.Button(tparts, button, control)
  
#    # insteon/{keypad or device} =====> btn/{keypad}
#   # Button is called from I2Entity
#   def Button(self, tparts, button, control):
#     self.Debug(f"Button [{tparts}] -> [{button}]")
#     topic = '/'.join(keypad, button)
#     topics = self.buttonmap.get(topic)
#     if topics: 
#       for t in topics:
#         self.mqtt.mqtt_publish(t, payload)

# #    self.mqtt.mqtt_publish(topic, control)

#   def Sensor(self, eparts, data):
#     topic = '/'.join([PREFIX_SENSOR]+eparts)
#     self.mqtt.mqtt_publish(topic, json.dumps(data))

    # eparts = None
    # if self.button:
    #   try:
    #     eparts = re.findall(self.button['regex'], entity_id)[0].split('_')
    #     slug = eparts.pop()
    #     if slug in self.slugs: slug = self.slugs.get(slug)
    #     eparts.append(slug)
    #   except: pass
    #   self.ISYButton(eparts, control)
    # elif self.sensor:
    #   try:
    #     eparts = re.findall(self.sensor['regex'], entity_id)[0].split('_')
    #   except: pass
    #   self.ISYSensor(eparts, data)
    # eparts = 
    # tail = eparts.pop()
    # self.Sensor(eparts, d)
    # elf.ISYSensor(data)
    # else: self.Warn(f"Unknown event {data['event']}")
    # if sconfig:
    #   t = sconfig.get('type')
    #   if t and t in ['power']:
    # event_sensor = self.args.get('event_sensor')
    # if 
    # type = 
    # if sensor:
    #   type = 
  
    # if sensor:
     
    #    and not self.sensor['regex']: self.Error(f"No sensor regex specified")
    # elif 
    

   

# class mqtt2x(u3.U3):
#   switch = {}
#   itype = None
#   buttonmap = {}
#   def initialize(self):
#     super().initialize()
#     self.itype = self.args.get('type')
#     if self.itype == 'i2': self.add_mqtt_trigger({'topic':'insteon/#'})
#     elif self.itype == 'ind': self.add_mqtt_trigger({'topic': f"{PREFIX_INDICATOR}/#"})
#     else: self.Error(f"Unknown indicator type {itype}")

#   def cb_mqtt(self, data):
#     topic = data.get('topic')
#     payload = data.get('payload')
#     tparts = topic.split('/')
#     self.Debug(f"Received {topic} with {payload}")
#     value = data.get('payload').upper()
#     if value in ['ON','OFF']:
#       if self.itype == 'i2': self.Button2Action(MqttTopic(tparts, self.args.get('ignore_tparts')), value)
#       elif self.itype == 'ind': self.ind2Switch(tparts, value)
#     else: self.Debug(f"Unknown payload {payload}")

#   def Button2Action(self, topic, payload):
#     topics = self.buttonmap.get(topic)
#     if topics: 
#       for t in topics:
#         self.mqtt.mqtt_publish(t, payload)
  
#   # ind/{device} => switch.ind_{device}
#   def Ind2Switch(self, eparts, data):
#     entity = 'switch.' + '_'.join(eparts)
#     if self.hass.entity_exists(entity):
#       if data == 'ON': self.hass.turn_on(entity)
#       elif data == 'OFF': self.hass.turn_off(entity)
#     else: self.Debug(f"Entity {entity} not found")
# endregion
# region Legacy Code
"""
DEBUG = True
def Debug(message): 
  if DEBUG: hass.services.call("notify", LOGGER, {"message": message }, False)
def Log(message): 
  hass.services.call("notify", LOGGER, {"message": message }, False)

AREAS = ['ao','master','kitchen','garage']
AREA_SYNONYMS = {
  'garage':'garage',
  'guest':'guest',
  'staircase':'staircase',
  'courtyard':'courtyard',
  'ao':'ao',
  'mbs':'mbs',
  'mbath':'mbath',
  'mbed':'mbed',
  'foyer':'foyer',
  'gym':'gym',
  'guest':'guest',
  'patio':'patio',
  'east':'east',
  'kp':'downstairs',
  'fr':'fr',
  'gar':'garage',
  'k':'kitchen',
  'g':'garage',
  'f':'foyer'
}
BTN_IGNORE = ['RR','OL','ST']

def PublishSensor(data):
    t = ['sensor']
    attr = None
    payload = None
    #Log(f"Sensor Data: {data}")
    control = data.get('control')
    entity_id = data.get('entity_id').split('.')[1]
    eparts = entity_id.split('_')
    Debug("\tControl {control}\n\tEntity {entity_id}\n\teparts {eparts}")
    Debug(f"\n\tControl {control}\n\tEntity {entity_id}\n\teparts {eparts}")
    index = None
    area = eparts.pop(0)
    t.append(area)
    device_type = None
    if eparts:
      if 'sensor' in eparts: eparts.remove('sensor')
      if 'duskdawn' in eparts: 
        eparts.remove('duskdawn')
        attr = 'is_dark'
      if 'door' in eparts: 
        device_type = 'door'
        attr = 'opening'
      for dt in ['battery','lux','dusk','heartbeat']:
        if dt in eparts:
          device_type = dt
          eparts.remove(device_type)
          break
      for prefix in ['s0','s1','s2','s3']:
        if prefix in eparts:
          index = prefix[1]
          eparts.remove(prefix)
          break
    else: Log(f"No eparts in data: {data}")

    if eparts: t.append('_'.join(eparts))
    if index: t.append(index)

    try: v = float(data.get('value'))
    except: Log(f"No value in data: {data}")

    if not attr:
      if control in ['DON','DOF']:
          attr = 'motion'
          payload = 'on' if control == 'DON' else 'off'
      elif control == 'CLITEMP':
          attr = 'temp'
          if v: payload = v/10
      elif control == 'LUMIN':
          attr = 'lux'
          if v: payload = v

    if attr: t.append(attr)

    topic = '/'.join(t)
    Log(f"Sensor: {entity_id}, Area {area}, Control {control}, value {v}")
    Debug(f"  ==> {payload} to {topic}")
    if payload: hass.services.call("mqtt", "publish", {"topic": topic, "payload": payload}, False)

def PublishButton(data):
    e = ""
    control = data.get('control')
    if control in BTN_IGNORE: return
    entity_id = data.get('entity_id')
  
    e = entity_id.split('.')[1].replace('btn_','')
    eparts = e.split('_')

    keypad = ""
    area = eparts.pop()
    button = '_'.join(eparts)

    for k, v in AREA_SYNONYMS.items():
        if area.startswith(k):
            keypad = area.replace(k,'')
            area = v
            break
    topic = '/'.join(['btn',area,keypad,button])
    if control[0] == 'D':
        payload = control[1:]
    else:
        payload = control
    Log(f"Entity: {e}, Area {area}, Keypad {keypad}, button {button}")
    hass.services.call("mqtt", "publish", {"topic": topic, "payload": payload}, False)

def PublishOther(data):
    e = ""
    path = ['isy']
    control = data.get('control')
    if control in BTN_IGNORE: return
    if control[0] == 'D':
      control = control[1:]
    entity_id = data.get('entity_id')
    
    e = entity_id.split('.')[1].replace('btn_','')
    Debug(f"\n\tOther entity: {e}")

    eparts = e.split('_')

    Debug(f"\teparts: {eparts}")
    for a in AREAS:
      if a in eparts:
        path.append(a)
        eparts.remove(a)
    path.extend(eparts)

    topic = '/'.join(path)
    payload = control
    Log(f"\tExperimental: {payload} to {topic}")
    hass.services.call("mqtt", "publish", {"topic": topic, "payload": payload}, False)

def Publish(data):
    e = ""
    d = ""
    control = data.get('control')
    entity_id = data.get('entity_id')

    d, e = entity_id.split('.')

    if d in ['binary_sensor']:
      PublishSensor(data)
    elif e.startswith('btn_'):
      PublishButton(data)
    else:
      PublishOther(data)

d = data.get('data')
rd = data.get('raw_data')
Publish(d)
"""
# endregion
# region Legacy YAML
"""
    - kitchen: 'k(\d{1})'
    - guest: 'guest(\d{1})'
    - mbed: 'mbed(\w{1})'
    - mbath: 'mbath(\w{1})'
    - mbs: 'mbs_(\w+)'
    - master: 'master_(\w+)'
    - courtyard: 'courtyard(\d{1})'
    - foyer: 'f([a-z1-9]{1})'
    - ao: 'ao(\d{1})'
    - ao: 'ao_(\w+)'
    - fr: 'fr(\d{1})'
    - fr: 'fr_(\w+)'
    - east: 'east(\d{1})'
    - garage: 'garage(\d{1})'
    - garage: 'garage_(\w+)'
    - patio: 'patio(\d{1})'
    - patio: 'patio_(\w+)'
    - house: 'house_(\w+)'
    - landscape: 'landscape_6'
    - gym
    - westroom
    - landing
    - northroom
    - bbq
    - entry
    

  slugs:
    - kitchen: 'k(\d{1})'
    - guest: 'guest(\d{1})'
    - mbed: 'mbed(\w{1})'
    - mbath: 'mbath(\w{1})'
    - mbs: 'mbs_(\w+)'
    - master: 'master_(\w+)'
    - courtyard: 'courtyard(\d{1})'
    - foyer: 'f([a-z1-9]{1})'
    - ao: 'ao(\d{1})'
    - ao: 'ao_(\w+)'
    - fr: 'fr(\d{1})'
    - fr: 'fr_(\w+)'
    - east: 'east(\d{1})'
    - garage: 'garage(\d{1})'
    - garage: 'garage_(\w+)'
    - patio: 'patio(\d{1})'
    - patio: 'patio_(\w+)'
    - house: 'house_(\w+)'
    - landscape: 'landscape_6'
    - gym
    - westroom
    - landing
    - northroom
    - bbq
    - entry

  
  AREA_SYNONYMS = {
    'garage':'garage',
    'guest':'guest',
    'staircase':'staircase',
    'courtyard':'courtyard',
    'ao':'ao',
    'mbs':'mbs',
    'mbath':'mbath',
    'mbed':'mbed',
    'foyer':'foyer',
    'gym':'gym',
    'guest':'guest',
    'patio':'patio',
    'east':'east',
    'kp':'downstairs',
    'fr':'fr',
    'gar':'garage',
    'k':'kitchen',
    'g':'garage',
    'f':'foyer'
  }

    - kitchen: 'k(\d{1})'
    - guest: 'guest(\d{1})'
    - mbed: 'mbed(\w{1})'
    - mbath: 'mbath(\w{1})'
    - mbs: 'mbs_(\w+)'
    - master: 'master_(\w+)'
    - courtyard: 'courtyard(\d{1})'
    - foyer: 'f([a-z1-9]{1})'
    - ao: 'ao(\d{1})'
    - ao: 'ao_(\w+)'
    - fr: 'fr(\d{1})'
    - fr: 'fr_(\w+)'
    - east: 'east(\d{1})'
    - garage: 'garage(\d{1})'
    - garage: 'garage_(\w+)'
    - patio: 'patio(\d{1})'
    - patio: 'patio_(\w+)'
    - house: 'house_(\w+)'
    - landscape: 'landscape_6'
    - gym
    - westroom
    - landing
    - northroom
    - bbq
    - entry
    

  slugs:
    - kitchen: 'k(\d{1})'
    - guest: 'guest(\d{1})'
    - mbed: 'mbed(\w{1})'
    - mbath: 'mbath(\w{1})'
    - mbs: 'mbs_(\w+)'
    - master: 'master_(\w+)'
    - courtyard: 'courtyard(\d{1})'
    - foyer: 'f([a-z1-9]{1})'
    - ao: 'ao(\d{1})'
    - ao: 'ao_(\w+)'
    - fr: 'fr(\d{1})'
    - fr: 'fr_(\w+)'
    - east: 'east(\d{1})'
    - garage: 'garage(\d{1})'
    - garage: 'garage_(\w+)'
    - patio: 'patio(\d{1})'
    - patio: 'patio_(\w+)'
    - house: 'house_(\w+)'
    - landscape: 'landscape_6'
    - gym
    - westroom
    - landing
    - northroom
    - bbq
    - entry

"""  
# endregion