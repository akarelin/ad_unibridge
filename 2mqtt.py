import u3
import json
import datetime
import re

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

class ToMQTT(u3.U3):
  button = {}
  sensor = {}
  ignore_events = []
  slugs = {}

  def initialize(self):
    super().initialize()
    self.ignore_events = self.args.get('ignore_events')
    self.slugs = self.args.get('slugs')
    
    self.button = self.args.get('button')
    if self.button:
      if not self.button['regex']: self.Error(f"No button regex specified")

    self.sensor = self.args.get('sensor')
    if self.sensor:
      if not self.sensor['regex']: self.Error(f"No sensor regex specified")

    self.Debug(f"Initialized remapper {self.args}")

  def cb_mqtt(self, data):
    self.I2Entity(self, data)

  def cb_event(self, data):
    if data['event'] in ['isy994_control']: self.ISYEntity(data)
    else: self.Warn(f"Unknown event {data['event']}")

  def ISYEntity(self, data):
    entity_id = data.get('entity_id')
    if not entity_id: 
      self.Warn(f"No entity_id in {data}")
      return
    
    control = data.get('control')
    if not control or control in self.ignore_events: 
      self.Debug(f"Ignoring control {control}")
      return

    try:
      eparts = re.findall(self.button['regex'], entity_id)[0].split('_')
      if eparts[-1] in self.slugs: eparts[-1]=self.slugs.get(eparts[-1])
      self.ISYButton(eparts, control)
      return
    except:  self.Debug(f"{entity_id} is not a button")

    try:
      eparts = re.findall(self.sensor['regex'], entity_id)[0].split('_')
      self.ISYSensor(eparts, data)
      return
    except:
      self.Debug(f"{entity_id} is not a sensor")

  def ISYSensor(self, eparts, data):
    self.Debug(f"Sensor {eparts} with {data}")

  def ISYButton(self, eparts, control):
    keypad = eparts.pop()
    button = eparts.join('_')
    self.Button(keypad, button, control)

  def I2Entity(self, data):
    topic = data.get('topic')
    payload = json.loads(data.get('payload'))
    if payload['reason'] not in ['device']: return
 
    eparts = topic.split('/')
    eparts.remove('kp')
    eparts.remove('state')
    
    button = eparts.pop()
    keypad = eparts.join('/')

    control = "F" if payload['mode'] in ['fast'] else ""
    control += payload['cmd'][:2].upper()
    self.Button(keypad, button, control)

  def Button(self, keypad, button, control):
    self.Debug(f"Button [{keypad}] -> [{button}]")
    topic = ['btn__',keypad,button].join('/')
    self.mqtt.mqtt_publish(topic, control)

    # {'entity_id': 'sensor.btn_pendant_ao1', 
    # 'control': 'DOF', 
    # 'value': 0,
    #  'formatted': 0,
    #  'uom': '', 
    # 'precision': '0',
    #  'metadata': 
    # {'origin': 'LOCAL', 
    # 'time_fired': '2021-06-18T04:29:35.468363+00:00', 
    # 'context': {...}}}

# LOGGER='DEBUG_ISY'
# DEBUG = True
# def Debug(message): 
#   if DEBUG: hass.services.call("notify", LOGGER, {"message": message }, False)
# def Log(message): 
#   hass.services.call("notify", LOGGER, {"message": message }, False)

# AREAS = ['ao','master','kitchen','garage']
# AREA_SYNONYMS = {
#   'garage':'garage',
#   'guest':'guest',
#   'staircase':'staircase',
#   'courtyard':'courtyard',
#   'ao':'ao',
#   'mbs':'mbs',
#   'mbath':'mbath',
#   'mbed':'mbed',
#   'foyer':'foyer',
#   'gym':'gym',
#   'guest':'guest',
#   'patio':'patio',
#   'east':'east',
#   'kp':'downstairs',
#   'fr':'fr',
#   'gar':'garage',
#   'k':'kitchen',
#   'g':'garage',
#   'f':'foyer'
# }
# BTN_IGNORE = ['RR','OL','ST']

# def PublishSensor(data):
#     t = ['sensor']
#     attr = None
#     payload = None
#     #Log(f"Sensor Data: {data}")
#     control = data.get('control')
#     entity_id = data.get('entity_id').split('.')[1]
#     eparts = entity_id.split('_')
#     Debug("\tControl {control}\n\tEntity {entity_id}\n\teparts {eparts}")
#     Debug(f"\n\tControl {control}\n\tEntity {entity_id}\n\teparts {eparts}")
#     index = None
#     area = eparts.pop(0)
#     t.append(area)
#     device_type = None
#     if eparts:
#       if 'sensor' in eparts: eparts.remove('sensor')
#       if 'duskdawn' in eparts: 
#         eparts.remove('duskdawn')
#         attr = 'is_dark'
#       if 'door' in eparts: 
#         device_type = 'door'
#         attr = 'opening'
#       for dt in ['battery','lux','dusk','heartbeat']:
#         if dt in eparts:
#           device_type = dt
#           eparts.remove(device_type)
#           break
#       for prefix in ['s0','s1','s2','s3']:
#         if prefix in eparts:
#           index = prefix[1]
#           eparts.remove(prefix)
#           break
#     else: Log(f"No eparts in data: {data}")

#     if eparts: t.append('_'.join(eparts))
#     if index: t.append(index)

#     try: v = float(data.get('value'))
#     except: Log(f"No value in data: {data}")

#     if not attr:
#       if control in ['DON','DOF']:
#           attr = 'motion'
#           payload = 'on' if control == 'DON' else 'off'
#       elif control == 'CLITEMP':
#           attr = 'temp'
#           if v: payload = v/10
#       elif control == 'LUMIN':
#           attr = 'lux'
#           if v: payload = v

#     if attr: t.append(attr)

#     topic = '/'.join(t)
#     Log(f"Sensor: {entity_id}, Area {area}, Control {control}, value {v}")
#     Debug(f"  ==> {payload} to {topic}")
#     if payload: hass.services.call("mqtt", "publish", {"topic": topic, "payload": payload}, False)

# def PublishButton(data):
#     e = ""
#     control = data.get('control')
#     if control in BTN_IGNORE: return
#     entity_id = data.get('entity_id')
  
#     e = entity_id.split('.')[1].replace('btn_','')
#     eparts = e.split('_')

#     keypad = ""
#     area = eparts.pop()
#     button = '_'.join(eparts)

#     for k, v in AREA_SYNONYMS.items():
#         if area.startswith(k):
#             keypad = area.replace(k,'')
#             area = v
#             break
#     topic = '/'.join(['btn',area,keypad,button])
#     if control[0] == 'D':
#         payload = control[1:]
#     else:
#         payload = control
#     Log(f"Entity: {e}, Area {area}, Keypad {keypad}, button {button}")
#     hass.services.call("mqtt", "publish", {"topic": topic, "payload": payload}, False)

# def PublishOther(data):
#     e = ""
#     path = ['isy']
#     control = data.get('control')
#     if control in BTN_IGNORE: return
#     if control[0] == 'D':
#       control = control[1:]
#     entity_id = data.get('entity_id')
    
#     e = entity_id.split('.')[1].replace('btn_','')
#     Debug(f"\n\tOther entity: {e}")

#     eparts = e.split('_')

#     Debug(f"\teparts: {eparts}")
#     for a in AREAS:
#       if a in eparts:
#         path.append(a)
#         eparts.remove(a)
#     path.extend(eparts)

#     topic = '/'.join(path)
#     payload = control
#     Log(f"\tExperimental: {payload} to {topic}")
#     hass.services.call("mqtt", "publish", {"topic": topic, "payload": payload}, False)

# def Publish(data):
#     e = ""
#     d = ""
#     control = data.get('control')
#     entity_id = data.get('entity_id')

#     d, e = entity_id.split('.')

#     if d in ['binary_sensor']:
#       PublishSensor(data)
#     elif e.startswith('btn_'):
#       PublishButton(data)
#     else:
#       PublishOther(data)

# d = data.get('data')
# rd = data.get('raw_data')
# Publish(d)
