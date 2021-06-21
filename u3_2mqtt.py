import u3
import json
import datetime
import re
import pprint

"""
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

class x2mqtt(u3.U3):
  button = {}
  sensor = {}
  slugs = {}

  def initialize(self):
    super().initialize()
    self.button = self.args.get('button')
    if self.button and not self.button['regex']: self.Error(f"No button regex specified")
    self.sensor = self.args.get('sensor')

    if self.sensor:
      if not self.sensor['regex']: self.Error(f"No sensor regex specified")

    self.Debug(f"Initialized remapper {self.args}")

  def cb_mqtt(self, data):
    topic = data.pop('topic')
    self.I2Entity(data)

  def cb_event(self, data):
    if data['event'] in ['isy994_control']: self.ISYEntity(data)
    else: self.Warn(f"Unknown event {data['event']}")

  def ISYEntity(self, data):
    entity_id = data.get('entity_id')
    if not entity_id: 
      self.Warn(f"No entity_id in {data}")
      return

    control = data.get('control').replace('D','')
    if not control or control in self.ignore_events: 
      self.Debug(f"Ignoring control {control}")
      return
    data['control'] = control

    if self.button:
      try:
        eparts = re.findall(self.button['regex'], entity_id)[0].split('_')
        slug = eparts.pop()
        if slug in self.slugs: slug = self.slugs.get(slug)
        eparts.append(slug)
      except: pass
      self.ISYButton(eparts, control)
    elif self.sensor:
      try:
        eparts = re.findall(self.sensor['regex'], entity_id)[0].split('_')
      except: pass
      self.ISYSensor(eparts, data)
    
  def ISYSensor(self, eparts, data):
    tail = eparts.pop()
    tail = tail[1] if tail in ['s1','s2'] else '' if tail in ['s','sensor'] else tail
    eparts.append(tail)
    extract = ['control','value','uom']
    d = {key: data[key] for key in extract}
    self.Sensor(eparts, d)

  def ISYButton(self, eparts, control):
    keypad = eparts.pop()
    button = '_'.join(eparts)
    self.Button(keypad, button, control)
  def cb_state(self, entity, attribute, old, new, kwargs):
    attributes = {}
    eparts = entity.split('.')[1].split('_')
    attributes = new.get('attributes')
    power_attributes = self.args.get('power_attributes')
    for k,v in attributes.items():
      if k in power_attributes:
        try:
          f = float(v)
          self.PowerSensor(eparts, f)
          return
        except: pass

  def PowerSensor(self, eparts, value):
    topic = '/'.join(['pwr__']+eparts)
    self.mqtt.mqtt_publish(topic, value)

  def I2Entity(self, data):
    topic = data.get('topic')
    payload = json.loads(data.get('payload'))
    if payload.get('reason') not in ['device']: return
 
    eparts = topic.split('/')
    eparts.remove('state')
    
    button = eparts.pop()
    keypad = '/'.join(eparts)

    control = "F" if payload['mode'] in ['fast'] else ""
    control += payload['state'][:2].upper()
    self.Button(keypad, button, control)

  def Button(self, keypad, button, control):
    self.Debug(f"Button [{keypad}] -> [{button}]")
    topic = '/'.join(['btn__',keypad,button])
    self.mqtt.mqtt_publish(topic, control)

  def Sensor(self, eparts, data):
    topic = '/'.join(['snsr__']+eparts)
    self.mqtt.mqtt_publish(topic, json.dumps(data))

class mqtt2x(u3.U3):
  switch = {}
  itype = None
  buttonmap = {}
  def initialize(self):
    super().initialize()
    self.itype = self.args.get('type')
    if self.itype == 'i2':
      self.LoadKeymap()
      self.add_mqtt_trigger({'topic':'insteon/#'})
    elif self.itype == 'ind':
      self.add_mqtt_trigger({'topic':'ind/#'})
    else:
      self.Error(f"Unknown indicator type {itype}")

  def LoadKeymap(self):
    bm = {}
    designators = self.args.get('designators')
    if designators: designators = [d.lower() for d in designators if d]
    for k,btns in self.keymap.items():
      if len(btns) != 8:
        self.Warn(f"Keypad {k}: len({btns}) == {len(btns)}")
        continue
      keypad = k.lower().split('/')
      base_topic = ['insteon']
      base_topic += keypad
      base_topic.append('set')
      if 'kp' in keypad: keypad.remove('kp')
      for i, indicator in enumerate(btns):
        if not indicator: continue
        topic = ['ind']
        keypad_areas = list(set(keypad) & set(self.areas))
        if len(keypad_areas) == 1: topic.append(keypad_areas[0])
        elif len(keypad_areas) > 1:
          self.Error(f"Keypad {keypad} has multiple areas {keypad_areas}")
          continue
        t1 = '/'.join(topic+[indicator.lower()])
        t2 = '/'.join(base_topic+[str(i)])
        if t1 in bm: bm[t1].append(t2)
        else: bm[t1] = [t2]
    self.Debug(pprint.pformat(bm))
    self.buttonmap = bm

  def cb_mqtt(self, data):
    topic = data.get('topic')
    payload = data.get('payload')
    eparts = topic.split('/')
    value = data.get('payload').upper()
    if value in ['ON','OFF']:
      if self.itype == 'i2': self.I2Indicator('ind/'+topic, value)
      elif self.itype == 'ind': self.ind2Indicator(eparts, value)
    else: self.Warn(f"Unknown payload {payload}")

  def I2Indicator(self, topic, payload):
    topics = self.buttonmap.get(topic)
    if topics:
      for t in topics: 
        self.mqtt.mqtt_publish(t, payload)
    
  def ind2Indicator(self, eparts, data):
    entity = 'switch.ind_' + '_'.join(eparts)
    if self.hass.entity_exists(entity):
      if payload == 'ON':
        self.hass.turn_on(entity)
      elif payload == 'OFF':
        self.hass.turn_off(entity)
    else:
      self.Debug(f"Entity {entity} not found")

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