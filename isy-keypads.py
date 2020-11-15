import unibridge
import json
import datetime


"""
isy2mqtt:
  module: isy-keypads
  class: discoverKeypads

  default_namespace: seven
  default_mqtt_namespace: mqtt
  debug: true

  triggers:
  - type: event
    event: isy994_control
    event_namespace: seven
  
<discovery_prefix>/device_automation/[<node_id>/]<object_id>/config
"""

class discoverKeypads(unibridge.App):
  def initialize(self):
    super().initialize()

    self.keypads = {}
    for e,s in self.hass.get_state('light').items():
      if 'light.btn_' in e:
        slug = e.split('_')[-1]
        self.keypads[slug] = {}
        self.keypads[slug]['buttons'] = []
        self.keypads[slug]['parent'] = e
        self.keypads[slug]['buttons'].append(e)

    for e,s in self.hass.get_state('sensor').items():
      if 'sensor.btn_' in e:
        slug = e.split('_')[-1]
        try:
          self.keypads[slug]['buttons'].append(e)
        except:
          self.warn("Unknown keypad {}", slug)

#    self.debug("Keypads {}",self.keypads)
  
  def trigger(self, s):
    self.debug("Event {}",s)
    keypad = s['entity_id'].split('_')[-1]
    button = s['entity_id'].split('_')[1]
    control = s['control']
    if control in ['DON','DOF','DFON','DFOF']:
      press = control[1:]
    else:
      self.warn("Unknown event")
      return
    
    topic = 'kpl/{}/{}'.format(keypad,button)
    
    self.debug("Topic {} payload {}",topic,press)
    self.mqtt.mqtt_publish(topic=topic, payload=press)
   
    
    # base_topic = 'homeassistant/device_automation/'
    # for k,buttons in keypads.items():
    #   topic = base_topic + k + '/'
    #   for b in buttons:
    #     t = topic + '/' + b + '/config'

    #     body['automation_type'] = 'trigger'
    #     body['topic'] = 


    #   keypad['namespace'] = self.default_namespace
    #   self.debug("Keypad {}",keypad)
    
    # self.debug("Keypads {}",keypads)

#    self.debug("Lights {}",buttons)
#    buttons += self.hass.get_state("switch")
#    self.debug("All buttons {}",buttons)

#    self.scene_list = self.args['scenes']
#    self.scene = {}
#    self.off_scenes = []
#    self.debug("Secenes {}", self.scene_list)

#    for scene_name in self.scene_list:
#      self.scene[scene_name] = self.load_scene(scene_name)
#      self.debug("Loaded scene {} with {}",scene_name,self.scene[scene_name])    

#class publisher(unibridge.App):
#  def initialize(self):
#    super().initialize()
#     self.members = []
#     self.effect = self.args.get('effect')
#     self.period = 60
#     self.precision = 5
#     self.brightness = None
#     self.default_brightness = 127
#     self.state = 'OFF'
#     if self.args.get('topic'):
#       self.topic_state = self.args['topic']+'/state'
#       self.topic_set = self.args['topic']+'/set'
#       self.initialize_triggers([{'type':'mqtt','topic':self.topic_set}])

#     self._init_members()
#     self.debug("Members {}",self.members)
#     self.api.run_minutely(self._timer, start = None)
#     self.update_members()

#   def update_members(self):
#     now = datetime.datetime.now()
#     angle_offset = now.minute*6

#     for member in self.members:
#       service_call = member['domain']+'/'
#       service_parameters = {}
#       service_parameters['entity_id'] = member['entity']
#       service_parameters['namespace'] = member['namespace']

#       if self.state == 'ON':
#         hue = (angle_offset + member['angle'])%360
#         service_call += 'turn_on'
#         service_parameters['hs_color'] = [hue,100]
#         service_parameters['brightness'] = self.brightness
#       elif self.state == 'OFF':
#         service_call += 'turn_off'
#       else:
#         self.error("Unkown state {}", self.state)
#         continue

#       self.debug("Calling {} => {}", service_call, service_parameters)
#       self.hass.call_service(service_call, **service_parameters)
#     self.publish_state()

#   def publish_state(self):
#     value = {}
#     value['state']=self.state
#     if self.state == 'ON':
#       if self.brightness:
#         value['brightness']=self.brightness
#       # if self.rgb_color:
#       #   value['rgb_color']=self.rgb_color
#     payload_json = json.dumps(value)
#     if self.topic_state:
#       self.debug("Status Publish to Topic {} Payload {}", self.topic_state, payload_json)
#       self.mqtt.mqtt_publish(topic=self.topic_state, payload=payload_json)
#     else:
#       self.debug("No status topic")

#   def _init_members(self):
#     members = self.args.get('members')
#     if not members:
#       self.error("No members!")
#       return
#     member_count = len(members)

#     for i, member in enumerate(members):
#       namespace = self.default_namespace
#       entity = None
#       domain = None
#       if '@' in member:
#         entity = member.split('@')[0].strip()
#         namespace = member.split('@')[1].strip()
#       else:
#         entity = member
#       if '.' in entity:
#         domain = entity.split('.')[0]
#       else:
#         domain = 'light'
#         entity = 'light.'+entity
      
#       member_object = {}      
#       member_object['entity'] = entity
#       member_object['namespace'] = namespace
#       member_object['domain'] = domain
#       if self.effect == 'colorloop': member_object['angle'] = int(i*360/member_count)
#       self.members.append(member_object)

#   def _load_state(self, s):
# #    self.debug("Extracting state from {}", value)
#     if s in ['OFF','ON']:
#       self.state = s
#       if s in ['ON']: self.brightness = self.default_brightness
#     else:
#       j = json.loads(s)
#       s = j.get('state')
#       if s not in ['ON','OFF']:
#         self.error("Unknown state {}",s)
#         return
#       else:
#         self.state = s
#       brightness = j.get('brightness',self.default_brightness)
#       if brightness: self.brightness = brightness
# #    self.debug("Extracted {} {}", self.state, self.brightness)
  
#   def _timer(self, kwargs):
#     if self.state == 'ON': self.update_members()
#     else: self.publish_state()

#   def trigger(self, s):
#     self._load_state(s)
#     self.update_members()