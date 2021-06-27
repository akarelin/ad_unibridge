import u3
import json
import datetime

"""
colorloop:
  module: group
  class: dynamic

  default_namespace: yaki
  default_mqtt_namespace: yaki_mqtt
  time: sensor.time

  name: "Main Colorloop"
  topic: 'main/colorloop'
  effect: colorloop  

  members:
    - hue_bedroom_bedsplash_1
    - hue_bedroom_bedsplash_2
"""

# region Constants
TYPE_LIGHT = 'light'

OFF = 'OFF'
ON = 'ON'
# endregion

class dynamic(u3.U3):
  members = []
  state = None
  topic = None
  brightness = 127

  def initialize(self):
    super().initialize()
    self.topic = self.args.get('topic')
    self.AddMembers()
    self.Debug(f"Members {self.members}")
    self.add_time_trigger({"interval": 60})
    self.add_mqtt_trigger({"topic": self.topic})

  def AddMembers(self):
    ms = self.args.get('members')
    if not ms:
      self.Error("No members!")
      return
    member_count = len(ms)
    
    for i, m in enumerate(ms):
      member = {}
#      prefix = None
      namespace = None
      domain = None
      entity_id = None
      name = None
      if ':' in m:
        namespace, name = m.split(':')
      else:
        namespace, name = self.u('namespace'),m
      
      if '.' in name:
        domain, entity = name.split('.')
      else:
        domain, entity = ["light",name]
    
      member['type'] = TYPE_LIGHT
      member['namespace'] = namespace
      member['name'] = name
      member['entity_id'] = '.'.join([domain, entity])

      member['angle'] = float(i*360/member_count)
      self.members.append(member)

# region _set_group
  def cb_timer(self, data):
    self.GroupUpdate()
  def cb_mqtt(self, data):
    payload = data.get('payload')
    if payload: 
      payload = payload.upper()
      if payload in [ON,OFF]: 
        self.state = payload
        self.GroupUpdate()

  def GroupUpdate(self):
    now = datetime.datetime.now()
    angle_offset = now.minute*6

    for m in self.members:
      if self.state == 'ON':
        angle = (angle_offset + m['angle'])%360
        self.MemberUpdate(m, ON, brightness = self.brightness, hue = angle)
      if self.state == 'OFF':
        self.MemberUpdate(m, OFF)
#    self.publish_state()
# endregion    

# region _set_member
  def MemberUpdate(self, member, cmd, brightness = 127, hue = None, saturation = 100):
    try:
      t = member['type']
    except:
      self.error(f"Unknown member {member}")
      return
# region LIGHT   
    if t == TYPE_LIGHT:
      e = None
      e = member['entity_id']
      namespace = member.get('namespace',self.u('namespace'))
      if cmd == ON:
        self.api.call_service("light/turn_on", entity_id = e, namespace = namespace, brightness = brightness, hs_color = [hue, saturation] if hue else None)
      elif cmd == OFF:
#        if self.get_state(e, namespace = namespace) != 'off':
        self.api.call_service("light/turn_off", entity_id = e, namespace = namespace)


      # if cmd == ON and hue:
      #   self.turn_on(e, brightness = brightness, hue = hue, saturation = saturation, namespace = member.get('namespace'))
      # elif cmd == ON and not hue:
      #   self.hass.turn_on(e, brightness = brightness, namespace = member.get('namespace'))
#        call = {}
#        call["brightness"] = brightness
#        if hue:
#          call["hs_color"] = [hue, saturation]
        # else:
        #   self.hass.turn_on(e, brightness = brightness, namespace = member.get('namespace'))
      # elif cmd == OFF: 
      #   self.hass.turn_off(e, namespace = member.get('namespace'))
# endregion
# endregion

