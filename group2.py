import unibridge
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
TYPE_Z2 = 'z2'
TYPE_LIGHT = 'light'

OFF = 'OFF'
ON = 'ON'
# endregion

class dynamic(unibridge.MqttDevice):
  members = []

  def initialize(self):
    super().initialize()
#    self.hass = self.get_plugin_api('deuce')

    self._init_members()
    self.debug("Members {}",self.members)
    self.add_time_trigger({"interval": 60})

  def _init_members(self):
    ms = self.args.get('members')
    if not ms:
      self.error("No members!")
      return
    member_count = len(ms)
    
    for i, m in enumerate(ms):
      member = {}
      prefix = None
      name = None
      if ':' in m:
        prefix, name = m.split(':')
      else:
        name = m

 #     self.debug("i {} m {} prefix {}",i,m,prefix)
      if prefix in ['Z2','z2','mqtt']:
        member['type'] = TYPE_Z2
        member['name'] = name
        member['topic'] = '/'.join(["z2mqtt",name,"set"])
      elif prefix in ['2','7','av','deuce','seven']:
        member['type'] = TYPE_LIGHT
        member['namespace'] = prefix
        member['name'] = name
        member['entity_id'] = "light."+name

      member['angle'] = float(i*360/member_count)
#      self.debug("Member {}",member)
      self.members.append(member)

# region _set_group
  def _set(self):
    now = datetime.datetime.now()
    angle_offset = now.minute*6
#    self.debug("Updating members {}",self.members)

    for m in self.members:
      if self.state == 'ON':
        angle = (angle_offset + m['angle'])%360
        self._set_member(m, ON, brightness = self.brightness, hue = angle)
      if self.state == 'OFF':
        self._set_member(m, OFF)
    self.publish_state()
    

# endregion    

# region _set_member
  def _set_member(self, member, cmd, brightness = 127, hue = None, saturation = 100):
    t = member['type']
# region Z2
    if t == TYPE_Z2:
      payload = {}
      topic = member['topic']
      if cmd == ON:
        payload['state'] = 'ON'
        payload['brightness'] = brightness
        if hue:
          payload['color'] = {"hue": hue, "saturation": saturation}
      elif cmd == OFF: payload['state'] = 'OFF'
      else: self.error("Unknown command {}", cmd)
      self.mqtt.mqtt_publish(topic, json.dumps(payload))
# endregion
# region LIGHT   
    elif t == TYPE_LIGHT:
      e = None
      e = member['entity_id']
      namespace = member.get('namespace')
      if cmd == ON:
        self.api.call_service("light/turn_on", entity_id = e, namespace = namespace, brightness = brightness, hs_color = [hue, saturation] if hue else None)
      elif cmd == OFF:
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

  def trigger(self, kwargs):
    self._set()