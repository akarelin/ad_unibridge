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
Z2 = 'z2'
LIGHT = 'light'

OFF = 'OFF'
ON = 'ON'
# endregion


# class static(unibridge.App):
#   def initialize(self):
#     super().initialize()

class dynamic(unibridge.MqttDevice):
  members = []

  def initialize(self):
    super().initialize()

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

      self.debug("i {} m {} prefix {}",i,m,prefix)
      if prefix == 'Z2':
        member['type'] = MQTT_Z2
        member['name'] = name
        member['topic'] = '/'.join(["z2mqtt",m,"set"])
      elif prefix in ['2','7','av']:
        member['type'] = HASS_LIGHT
        member['namespace'] = prefix
        member['name'] = name
      member['angle'] = float(i*360/member_count)
      self.debug("Member {}",member)
      self.members.append(member)

  def _set(self):
    now = datetime.datetime.now()
    angle_offset = now.minute*6
    self.debug("Updating members {}",self.members)

    for m in self.members:
      if self.state == 'ON':
        angle = (angle_offset + m['angle'])%360
        self._set_z2(m['topic'], ON, self.brightness, angle)
      if self.state == 'OFF':
        self._set_z2(m['topic'], OFF)
    self.publish_state()

  def _set_z2(self, topic, cmd, brightness = 127, hue = None, saturation = 100):
    payload = {}
    
    if cmd == ON:
      payload['state'] = 'ON'
      payload['brightness'] = brightness
      if hue:
        payload['color'] = {"hue": hue, "saturation": saturation}
    elif cmd == OFF: payload['state'] = 'OFF'
    else: self.error("Unknown command {}", cmd)
    
#    self.debug("\n\tTopic {}\n\tPayload {}", topic, json.dumps(payload))
    self.mqtt.mqtt_publish(topic, json.dumps(payload))
    
  def _set_hassio(self, entity, cmd, namespace = None, brightness = 127, hue = None, saturation = 100):
    service = None
    call = {}
    call["namespace"] = namespace
    call["entity_id	"] = entity

    if cmd == ON:
      service = "ligh.turn_on"
      call["brightness"] = brightness
      if hue:
        call["hs_color"] = [hue, saturation]
    elif cmd == OFF: 
      service = "ligh.turn_off"
    self.api.call_service(service, call)

    
  def trigger(self, kwargs):
    self._set()