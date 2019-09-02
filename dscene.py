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
#    super().initialize()
    self.scene_list = []
    self.scene_list = self.args['scenes']
    self.scene = {}
    
    self.load_members()
#    self.debug("Scenes {} {}",self.scene['evening'],self.scene['morning'])
    self.listen_event(self._event, self.args['event'], namespace=self.args['event_namespace'])

  def DoIt(self, name):
    self.debug("{}",self.scene[name])
    for e,v in self.scene[name].items():
      # try:
      #   params = v['params']
      # except:
      #   params = ''
      params = v
#      n = v['namespace']
#      del params['namespace']
      s = v['service']
      del params['service']
      params['entity_id'] = e
      
      self.debug("Calling service {} with params {}",s,params)
      
      if 'brightness_pct' in v:
        self.call_service(s, namespace = v['namespace'], entity_id = e, brightness_pct = v['brightness_pct'])
      else:
        self.call_service(s, namespace = v['namespace'], entity_id = e)

  def load_members(self):
    for s in self.scene_list:
      self.scene[s] = {}
      for m,sv in self.args["members"].items():
        params = {}
        service = ''
        command = ''
        if '.' not in m:
          m = 'light.'+m
        if '@' in m:
          e = m.split('@')[0].strip()
          n = m.split('@')[1].strip()
        else:
          e = m
          n = self.args['default_namespace']
        try: command = sv[s]
        except: break

        if command in ['on','true']:
          service = 'light/turn_on'
        elif command in ['off','false']:
          service = 'light/turn_off'
        else:
          try:
            params['brightness_pct'] = int(command)
            service = 'light/turn_on'
          except:
            self.error("Scene {} member {} unknown command {}",s,m,command)
            break
        self.scene[s][e] = {}
        self.scene[s][e]['service'] = service
        self.scene[s][e]['namespace'] = n
        if params:
          self.scene[s][e]['params'] = params

  def _event(self, evemt_name, data, kwargs):
    scene = data['scene']
    if scene not in self.scenes:
      self.error("Unknown scene {}", scene)
      return



  
  # def cbEvent(self, event_name, data, kwargs):
  #   try:
  #     command = data['control']
  #   except:
  #     command = 'UNKNOWN'
  #   self.debug("Event {} fired by {}", command, data['entity_id'])
  #   if data['entity_id'] not in self.buttons:
  #     self.debug("Not our entity {}", data['entity_id'])
  #     return
  #   if command in ['DON']:
  #     self.debug("Turning on {}", self.entity_id)
  #     self.turn_on(self.entity_id)
  #   elif command in ['DOF', 'DFOF']:
  #     self.debug("Turning off {}", self.entity_id)
  #     self.turn_off(self.entity_id)
  #   elif command in ['DFON']:
  #     self.debug("Turning on full {}", self.entity_id)
  #     self.turn_on(self.entity_id, brightness = 255)
  #   else:
  #     self.debug("Not our command {}", command)
# If its DON, DOFF on any of our buttons - change the status of entity


