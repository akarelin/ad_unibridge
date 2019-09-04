import unibridge
import json
import re
from datetime import datetime, time

"""
247:
  module: scene
  class: scene

  event: SCENE
  event_namespace: cv

  scenes:
  - evening
  - night
  - sleep
  - morning

  default_namespace: cv
  members:
    front_lamps @ cv:
      evening: 33
    courtyard_colorloop:
      evening: 33
      night: 16
      sleep: 'off'
      day: 'off'      
    hue_front_color @ cv_primary:
      evening: 81,255,101 @ 50
      night: 81,255,101 @ 33
      sleep: 81,255,101 @ 25
      day: 'off'
    climate.downstairs:
      home: cool
      sleep: 'off'
      away: 'off'      
"""

class scene(unibridge.AppHass):
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
      self.debug("Calling {} on {} for {} with {}",s,v['namespace'],e,params)
      
      if 'brightness_pct' in params:
        self.call_service(s, namespace = v['namespace'], entity_id = e, brightness_pct = params['brightness_pct'])
      elif 'preset_mode' in params:
        self.call_service(s, namespace = v['namespace'], entity_id = e, preset_mode = params['preset_mode'])
      elif 'rgb_color' in params:
        self.call_service(s, namespace = v['namespace'], entity_id = e, brightness_pct = params['brightness_pct'], rgb_color = params['rgb_color'])
      else:
        self.call_service(s, namespace = v['namespace'], entity_id = e)

  def load_members(self):
    for s in self.scene_list:
      self.scene[s] = {}
      for m,sv in self.args["members"].items():
        params = {}
        service = ""
        command = ""
## Extract namespace
        if '@' in m:
          e = m.split('@')[0].strip()
          n = m.split('@')[1].strip()
        else:
          e = m
          n = self.args['default_namespace']
## Extract command
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
          if '@' in str(command):
            try:
              service = 'light/turn_on'
              params['brightness_pct'] = int(command.split('@')[1])
              params['rgb_color'] = command.split('@')[0].strip()
            except:
              self.error("Scene={} member={} Unknown command {}",s,m,command)
              continue
          elif command in ['on','true']:
            service = 'light/turn_on'
          elif command in ['off','false','0']:
            service = 'light/turn_off'
          else:
            try:
              if '@' in str(command):
                params['brightness_pct'] = int(command.split('@')[1].strip())
                params['rgb_color'] = command.split('@')[0].strip()
                service = 'light/turn_on'
              else:
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
    self.debug("Event {} with {}",event_name,data)
    scene = data['scene']
    if scene not in self.scene_list:
      self.error("Unknown scene {}", scene)
      return
    self.DoIt(scene)