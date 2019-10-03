import unibridge
import datetime

"""
247:
  module: scene
  class: scene

  triggers:
    - type: event
      event: SCENE
      event_namespace: cv
    - type: mqtt
      topic: 'mode/time/state'

  scenes:
    evening: 
#      time: sunset-30
    night: 
#      time: 22:00
    sleep: 
#      time: 00:30
      default_action: 'off'
    morning:
#      time: sunrise+0
      default_action: 'off'

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

ON = "turn_on"
OFF = "turn_off"

class scene(unibridge.App):
  def initialize(self):
    super().initialize()
    self.scene_list = []
    self.scene_list = self.args['scenes']
    self.scene = {}
    self.off_scenes = []

    for scene_name in self.scene_list:
      self.scene[scene_name] = self.load_scene(scene_name)
      self.debug("Loaded scene {} with {}",scene_name,self.scene[scene_name])

    # self.api.run_at_sunrise(self._sunrise, offset=0)
    # self.api.run_at_sunset(self._sunset, offset=0)
    # self.api.run_daily(self._night, datetime.time(22, 00, 0))
    # self.api.run_daily(self._sleep, datetime.time(00, 30, 0))
#    self.hass.listen_event(self._event, self.args['event'])

#    for topic in self.topics:
#      self.mqtt.mqtt_subscribe(topic)
#      self.mqtt.listen_event(self._mqtt, "MQTT_MESSAGE", topic = topic)

  def immediate(self, scene_name):
    if scene_name not in self.scene_list:
      self.error("Unknown immediate scene {}", scene_name)
      return
    self.debug('Executing immediate scene {}', scene_name)

    scene = self.scene[scene_name]
    for member in scene:
      try:
        service = member.pop('service_call')
      except:
        continue
      self.debug("Calling service {} => {}",service,member)
      self.hass.call_service(service, **member)

  def load_scene(self, scene_name):
    default_action = self.args['scenes'][scene_name].get('default_action')
    if default_action == 'off': self.off_scenes.append(scene_name)
   
    scene_members = []
#    self.debug("Loading scene {} from {}",scene_name,self.args["members"])
    for member,member_actions in self.args["members"].items():
      action = None
      if member_actions:
        action = member_actions.get(scene_name)
      if not action:
        if scene_name in self.off_scenes:
          action = 'off'
        else:
          self.debug("Member {} is not in scene {}",member,scene_name)
          continue

      method = ""
      namespace = ""
      entity_id = ""
      domain = ""
      params = {}
## Extract namespace and entity_id
      if '@' in member:
        entity_id = member.split('@')[0].strip()
        namespace = member.split('@')[1].strip()
      else:
        entity_id = member
        namespace = self.default_namespace
      if '.' in entity_id:
        domain = entity_id.split('.')[0]
      else:
        domain = 'light'
        entity_id = 'light.'+entity_id
##
## Build service call
##
## Light
      if domain in ['light']:
        brightness=""
        if '@' in str(action):
          method = ON
          try:
            brightness = int(action.split('@')[1].strip())
            rgb = action.split('@')[0].strip().split(',')
            params['rgb_color'] = rgb
          except:
            self.error("[AT] {} => {} =???=> {}",scene_name,member,action)
            continue
        elif action in ['on','true']:
          method = ON
        elif action in ['off','false','0',0]:
          method = OFF
        else:
          method = ON
          brightness = action

        if brightness:
          if brightness == 1:
            params['brightness'] = 1
          elif brightness > 1:
            params['brightness'] = int(brightness*2.55)
          else:
            self.error("[Brightness] {} => {} =???=> {} {}",scene_name,member,method,brightness)
            continue
# ## Climate
#         elif domain in ['climate']:
#           if action in ['off']:
#             method = OFF
#           elif action in ['auto','cool','heat']:
#             method = 'set_hvac_mode'
#             params['hvac_mode'] = command
#           elif action in ['home','away']:
#             method = 'set_preset_mode'
#             params['preset_mode'] = command
#           else:
#             self.error("Scene {} member {} unknown action {}",scene_name,member,action)
        # else:
        #   self.error("Scene {} member {} unknown domain  {}",scene_name,member,domain)
## Return scene_memebrs
      scene_member = {}
      scene_member['service_call'] = domain+'/'+method
      scene_member['entity_id'] = entity_id
      scene_member['namespace'] = namespace
      scene_member.update(params)
      scene_members.append(scene_member)
    return scene_members

  def _event(self, scene):
    self.immediate(scene)