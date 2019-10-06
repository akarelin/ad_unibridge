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

class dynamic(unibridge.App):
  def initialize(self):
    super().initialize()
    self.members = []
    self.effect = self.args.get('effect')
<<<<<<< HEAD
    self.period = 60
    self.precision = 5
    self.brightness = None
    self.default_brightness = 127
=======

    if self.effect == 'colorloop':
      self.init_colorloop()
    self.init_mqtt()

  def init_mqtt(self):
    topic = self.args["topic"]
    self.topic_state = topic + '/state'
    self.topic_set = topic + '/set'
    trigger = {'type':'mqtt','topic':self.topic_set}
    self.initialize_triggers([trigger])

  def init_colorloop(self):
    try: self.period = int(self.args["period"])
    except: self.period = 60
    try: self.precision = int(self.args["precision"])
    except: self.precision = 5
    interval = self.precision

    # if self.timer:
    #   self.debug("Cancelling timer")
    #   self.api.cancel_timer(self.timer)
    #   self.debug("API {} {}",type(self.api),repr(self.api))
    # if self.state == 'ON':
    if not self.timer:
      start = datetime.datetime.now() + datetime.timedelta(0, interval)
      self.timer = self.api.run_every(self._timer, start = start, interval = interval)

  def light_on(self, brightness = 128):
    self.state = 'ON'
    self.brightness = brightness
    self.debug("Switching on")
    self._set()
  def light_off(self):
>>>>>>> e01953cf6eecd293cac0d53e34d04ba4cfc7f841
    self.state = 'OFF'
    if self.args.get('topic'):
      self.topic_state = self.args['topic']+'/state'
      self.topic_set = self.args['topic']+'/set'
      self.initialize_triggers([{'type':'mqtt','topic':self.topic_set}])

    self.load_members()
    self.debug("Members {}",self.members)
#    self.mqtt.listen_event(self._event, 'MQTT_MESSAGE', topic = self.topic_set)
    self.api.run_minutely(self._timer, start = None)
    self._update()

  # def turn_on(self, brightness = 128):
  #   self.state = 'ON'
  #   self.brightness = brightness
  #   self._update()
  # def turn_off(self):
  #   self.state = 'OFF'
  #   self._update()
  
  def _update(self):
    now = datetime.datetime.now()
    angle_offset = now.minute*6

    for member in self.members:
      service_call = member['domain']+'/'
      service_parameters = {}
      service_parameters['entity_id'] = member['entity']
      service_parameters['namespace'] = member['namespace']

      if self.state == 'ON':
        hue = (angle_offset + member['angle'])%360
        service_call += 'turn_on'
        service_parameters['hs_color'] = [hue,100]
        service_parameters['brightness'] = self.brightness
      elif self.state == 'OFF':
        service_call += 'turn_off'
      else:
        self.error("Unkown state {}", self.state)
        continue

      self.debug("Calling {} => {}", service_call, service_parameters)
      self.hass.call_service(service_call, **service_parameters)
    self.publish()

  def load_members(self):
    members = self.args.get('members')
    if not members:
      self.error("No members!")
      return
    member_count = len(members)

    for i, member in enumerate(members):
      namespace = self.default_namespace
      entity = None
      domain = None
      if '@' in member:
        entity = member.split('@')[0].strip()
        namespace = member.split('@')[1].strip()
      else:
        entity = member
      if '.' in entity:
        domain = entity.split('.')[0]
      else:
        domain = 'light'
        entity = 'light.'+entity
      
      member_object = {}      
      member_object['entity'] = entity
      member_object['namespace'] = namespace
      member_object['domain'] = domain
      if self.effect == 'colorloop': member_object['angle'] = int(i*360/member_count)
      self.members.append(member_object)

  def extract(self, value):
#    self.debug("Extracting state from {}", value)
    if value in ['OFF','ON']:
      self.state = value
      if value in ['ON']: self.brightness = self.default_brightness
    else:
      jv = json.loads(value)
      state = jv.get('state')
      if state not in ['ON','OFF']:
        self.error("Unknown state {}",state)
        return
      else:
        self.state = state
      brightness = jv.get('brightness',self.default_brightness)
      if brightness: self.brightness = brightness
#    self.debug("Extracted {} {}", self.state, self.brightness)
  
  def publish(self):
    value = {}
    value['state']=self.state
    if self.state == 'ON':
      if self.brightness:
        value['brightness']=self.brightness
      # if self.rgb_color:
      #   value['rgb_color']=self.rgb_color
    payload_json = json.dumps(value)
    if self.topic_state:
      self.debug("Status Publish to Topic {} Payload {}", self.topic_state, payload_json)
      self.mqtt.mqtt_publish(topic=self.topic_state, payload=payload_json)
    else:
      self.debug("No status topic")

  def _timer(self, kwargs):
    if self.state == 'ON': self._update()
    else: self.publish()

  def _event(self, value):
    self.extract(value)
    self._update()