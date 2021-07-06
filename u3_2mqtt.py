# region Imports and Constants
import u3
from u3 import MqttTopic
import typing
from typing import List, Dict
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

""" example
  remapper:
    module: 2mqtt
    class: ToMQTT
    debug: True
    default_namespace: deuce

    button:
      regex: '^(?:sensor|light|switch)(?:\.btn_)(.+)$'
      ignore_events:
        - RR
        - OL
        - ST

    sensor: '^(?:binary_)?sensor.(.+)?'

    triggers:
      - type: event
        event: isy994_control
"""

def isy_DataFromEvent(data, ignore_events = None):
  event = data.pop('event')
  entity = data.pop('entity_id')
  if not event or event not in ['isy994_control']: return
  if entity:
    control = data.pop('control')
    if control and control not in ignore_events: 
      data['control'] = control
      data['entity'] = entity
      return data
    # else: self.Debug(f"Ignoring control {control}")
    # else: self.Warn(f"No entity_id in {data}")

class sensor2mqtt(u3.U3):
  """
    isy_sensor_2mqtt:
      module: u3_2mqtt
      class: sensor2mqtt
      dependencies: universe
      debug: False
      sensor:
        regex: '^(?:binary_)?sensor.(.+)?'
      triggers:
        - type: event
          event: isy994_control

    power_switch_2mqtt:
      module: u3_2mqtt
      class: sensor2mqtt
      dependencies: universe
      debug: false
      power_attributes:
        - current_power_w
        - power
      triggers:
        - type: state
          entity: switch  
  """
  sensor_regex = None
  sensor_attributes = []
   
  def initialize(self):
    super().initialize()
    sconfig = self.args.get('sensor')
    if sconfig: 
      trigger = sconfig.get('trigger')
      if trigger == 'event': 
        type = sconfig.get('type')
        if type == 'isy994_event': 
          regex = sconfig.get('regex')
          if regex:
            self.sensor_regex = regex
            self.add_event_trigger({'event': 'isy994_control'})
          else: self.Error(f"Invalid Regex")
        else: self.Error(f"Invalid Type")
      elif trigger == 'state':
        type = sconfig.get('type')
        if type == 'power': 
          attributes = sconfig.get('attributes')
          if attributes:
            if isinstance(attributes,List): self.sensor_attributes = attributes
            else: self.sensor_attributes = [attributes]
            self.add_state_trigger({'entity': 'switch'})
        else: self.Error(f"Invalid type")
      else: self.Error(f"Invalid trigger")
    else: self.Error(f"No sensor specified")
     
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
  def cb_event(self, data):
    data = isy_DataFromEvent(data, self.ignore_events)
    self.ISYSensor(data)

  def cb_state(self, entity, attribute, old, new, kwargs):
    value = 0.0
    eparts = []
    eparts = entity.split('.')[1].split('_')    
    if 'power' in eparts: eparts.remove('power')
    attributes = {}
    attributes = new.get('attributes')
    for k,v in attributes.items():
      if k in self.sensor_attributes:
        try:
          value = float(v)
          topic = '/'.join([PREFIX_POWER]+eparts)
          self.mqtt.mqtt_publish(topic, value)
          return
        except: pass

class button2event(u3.U3):
  """
    button_isy_2event:
      module: u3_2mqtt
      class: button2event
      dependencies: universe
      debug: False
      button:
        regex: '^(?:sensor|light|switch)(?:\.btn_)(.+)$'
      triggers:
        - type: event
          event: isy994_control

    button_i2_2event:
      module: u3_2mqtt
      class: button2event
      dependencies: universe
      debug: False

      triggers:
        - type: mqtt
          topic: 'insteon/kp/#'
  """
  button_regex = None

  def initialize(self):
    super().initialize()
    bconfig = self.args.get('button')
    if bconfig: 
      trigger = bconfig.get('trigger')
      if trigger == 'event': 
        type = bconfig.get('type')
        if type == 'isy994_event': 
          regex = bconfig.get('regex')
          if regex:
            self.button_regex = regex
            self.add_event_trigger({'event': 'isy994_control'})
          else: self.Error(f"Invalid Regex")
        else: self.Error(f"Invalid Type")
      elif trigger == 'mqtt':
        type = bconfig.get('type')
        if type == 'i2': 
          for topic in self.u('keypad_topics'):
            self.add_mqtt_trigger({'topic': topic})
        else: self.Error(f"Invalid type")
      else: self.Error(f"Invalid trigger")
    else: self.Error(f"No button specified")
    return

  def cb_event(self, data):
    data = isy_DataFromEvent(data, self.ignore_events)
    eparts = []
    entity = data.get('entity')
    try: eparts = re.findall(self.button_regex, entity)[0].split('_')
    except: return
    if eparts: self.ISYButton(eparts, data)
  def ISYButton(self, eparts, data):
    tail = eparts.pop()
    eparts.append(tail)

  def cb_mqtt(self, data):
    topic = data.get('topic')
    payload = data.get('payload')
    self.I2Button(topic, payload)
  def I2Button(self, topic, payload):
    try: 
      a = self.u('map_topic2action').get(topic)
    except:
      self.Debug(f"Exception for some reason")
    if not a: return
    action = a['action']
    area = a.get('area')

    p = {}
    reason = None
    try:
      p = json.loads(payload)
      reason = p['reason']
    except: return
    if reason not in ['device']: return
    control = ('F' if p['mode'].upper() in ['FAST'] else "") + p['state'][:2].upper()
    
    t = p['timestamp']
    delta = self.api.get_now_ts() - t
    if delta > 10: return

    topic = 'act'
    if area: topic = topic+'/'+area
    if action: topic = topic+'/'+action
    payload = control
    self.mqtt.mqtt_publish(topic, payload)


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