#import appdaemon.plugins.hass.hassapi as hass
import unibridge
import json
#from datetime import datetime, time
import datetime

"""
colorloop:
  module: group
  class: group

  name: "Main Colorloop"
  topic: 'main/colorloop'

  entities:
    - light.kitchen_undercabinet
    - light.kitchen_ambient
    - light.desk_ambient
#  rgb_color: [255,116,22]
  effect: colorloop
"""

class group(unibridge.App):
  def initialize(self):
    super().initialize()
    self.timer = None
    self.state = 'OFF'
    self.entities = []

    self.entities = self.args["entities"]
    self.brightness = self.args.get('brightness',128)
    self.rgb_color = self.args.get('rgb_color')
    self.effect = self.args.get('effect')

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
    if self.state == 'ON':
      if self.timer: self.api.cancel_timer(self.timer)
      start = datetime.datetime.now() + datetime.timedelta(0, interval)
      self.timer = self.api.run_every(self._timer, start = start, interval = interval)

  def light_on(self, brightness = 128):
    self.state = 'ON'
    self.brightness = brightness
    self.debug("Switching on")
    self._set()
  def light_off(self):
    self.state = 'OFF'
    self.debug("Switching off")
    self._set()

  def _set(self):
    self.debug("Setting entities {} effect {}",self.entities,self.effect)
    if self.effect == 'colorloop':
      self._set_colorloop()
      # if self.state == 'OFF' and self.timer:
      #   self.api.cancel_timer(self.timer)
      # elif self.state == 'ON' and not self.timer:
      #   self.init_colorloop()
    else:
      self._set_color()
    self._publish()
  
  def _set_color(self):
    self.debug("Setting entities {}, brightness {}, color",self.entities,self.brightness,self.rgb_color)
    for i,entity in enumerate(self.entities):
      if self.state == 'ON':
        self.debug("Turning on entity {}, brightness {}, color",entity,self.brightness,self.rgb_color)
        self.hass.turn_on(entity, rgb_color=self.rgb_color, brightness=self.brightness)
      elif self.state == 'OFF':
        self.debug("Turning off entity {}",entity)
        self.hass.turn_off(entity)
      else:
        self.debug("Unkown state {}".format(self.state))
   
  def _set_colorloop(self):
    if self.state == 'ON' and not self.timer:
      self.init_mqtt()
    
    second = datetime.datetime.now().second
    modulo=(second%(self.period*60))/10

    for i,entity in enumerate(self.entities):
      if self.state == 'ON':
        hscolor=int((modulo+i*360/len(self.entities))%360)
        self.hass.turn_on(entity, hs_color=[hscolor,100], brightness=self.brightness)
      elif self.state == 'OFF':
        self.hass.turn_off(entity)
      else:
        self.error("Unkown state {}".format(self.state))
    if self.state == 'OFF' and self.timer:
      self.api.cancel_timer(self.timer)
      self.timer = None

  def _publish(self):
    status = {}
    status['state']=self.state
    if self.state == 'ON':
      if self.brightness:
        status['brightness']=self.brightness
      if self.rgb_color:
        status['rgb_color']=self.rgb_color
    status_json = json.dumps(status)
    if self.topic_state:
      self.debug("Status Publish to Topic {} Payload {}", self.topic_state, status_json)
      self.hass.call_service("mqtt/publish", topic=self.topic_state, payload=status_json)
    else:
      self.debug("No status topic")

  def _timer(self, kwargs):
    self._set()

  def _event(self, data):
    if data in ['ON','OFF']: 
      self.state = data
      self._set()
      return

    json_data = json.loads(data)
    state = json_data.get('state')
    if state not in ['ON','OFF']:
      self.warn("Invalid data {}", data)
      return

    if state == 'OFF':
      self.light_off()
      return

    brightness = json_data.get('brightness')
    if brightness:
      self.light_on(brightness)
    else:
      self.light_on()
