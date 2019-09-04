import unibridge
import json
from datetime import datetime, time

"""
247:
  module: dscene
  class: dscene

  event: DSCENE
  event_namespace: cv

  scenes:
  - evening
  - night
  - sleep
  - morning

  members:
  - front_lamps @ cv:
      evening: 33
  - front_landscape @ cv:
      evening: 66
  - courtyard @ cv:
      evening: on
  - courtyard_colorloop:
      evening: 33
  - upstairs_corridor_color:
      evening: 50
  - stairs_color:
      evening: 50
  - empty_office_ambient:
      evening: 33
  - family_room_ambient:
      evening: 25
  - stairs_ambient:
      evening: 66
  - entry_ambient:
      evening: 75
  - downstairs_corridor_undercabinet:
      evening: 33
  - living_room_ambient:
      evening: 75
  - dining_ambient:
      evening: 33
  - kitchen_overcabient:
      evening: on
  - kitchen_undercabinet:
      evening: on
"""

class dscene(unibridge.AppHass):
  def initialize(self):
    self.scene_list = []
    self.scene_list = self.args['scenes']
    self.scene = {}
    
    self.load_members()
    for s in self.scene_list:
      self.debug("Scene {} parameters {}",s, self.scene[s])
    self.listen_event(self._event, self.args['event'], namespace=self.args['event_namespace'])

  def DoIt(self, name):
    self.debug("Executing {} with {}", name, self.scene[name])
    for e,v in self.scene[name].items():
      s = v['service']
      params = {}

      if 'params' in v:
        params = v['params']
      self.debug("Calling service {} with {}",s,params)
      
      if 'brightness_pct' in params:
        self.call_service(s, namespace = v['namespace'], entity_id = e, brightness_pct = params['brightness_pct'])
      elif 'preset_mode' in params:
        self.call_service(s, namespace = v['namespace'], entity_id = e, preset_mode = params['preset_mode'])
      else:
        self.call_service(s, namespace = v['namespace'], entity_id = e)

  def load_members(self):
    for s in self.scene_list:
      self.scene[s] = {}
      for m,sv in self.args["members"].items():
        params = {}
        service = ''
        command = ''
## Extract namespace
        if '@' in m:
          e = m.split('@')[0].strip()
          n = m.split('@')[1].strip()
        else:
          e = m
          n = self.args['default_namespace']
        try: command = sv[s]
        except: continue
## Determine type
        if '.' in m:
          t = e.split('.')[0]
        else:
          t = 'light'
          e = 'light.'+e
## Determine call
        if t in ['light']:
          if command in ['on','true']:
            service = 'light/turn_on'
          elif command in ['off','false']:
            service = 'light/turn_off'
          else:
            try:
              params['brightness_pct'] = int(command)
              service = 'light/turn_on'
            except:
              self.error("Scene {} member {} unknown {} command {}",s,m,t,command)
              continue
        elif t in ['climate']:
          if command in ['off']:
            service = 'climate/turn_off'
          elif command in ['auto','cool','heat']:
            service = 'climate/set_hvac_mode'
            params['hvac_mode'] = command
          elif command in ['home','away']:
            service = 'climate/set_preset_mode'
            params['preset_mode'] = command
          else:
            self.error("Scene {} member {} unknown {} command {}",s,m,t,command)
        else:
          self.error("Scene {} member {} unknown type {}",s,m,t)

        self.scene[s][e] = {}
        self.scene[s][e]['service'] = service
        self.scene[s][e]['namespace'] = n
        if params:
          self.scene[s][e]['params'] = params

  def _event(self, event_name, data, kwargs):
    scene = data['scene']
    if scene not in self.scenes:
      self.error("Unknown scene {}", scene)
      return
    self.DoIt(scene)