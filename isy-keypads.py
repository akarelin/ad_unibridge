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

class btn(unibridge.App):
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
  
  def trigger(self, data):
    self.debug("Event {}", data)
    if '.btn_' not in data:
      return
    keypad = data['entity_id'].split('_')[-1]
    button = data['entity_id'].split('_')[1]
    control = data['control']
    if control in ['DON','DOF','DFON','DFOF']:
      press = control[1:]
    else:
      self.warn("Unknown event")
      return
    
    topic = 'btn/{}/{}'.format(keypad,button)
    
    self.debug("Topic {} payload {}",topic,press)
    self.mqtt.mqtt_publish(topic=topic, payload=press)

class ind(unibridge.App):
  def initialize(self):
    super().initialize()
    self.indicators = []
    for e,s in self.hass.get_state('switch').items():
      if 'switch.ind_' in e:
        slug = e.split('_')[-1]
        self.indicators.append(slug)
    
    self.mqtt.mqtt_subscribe("ind/#")
    self.mqtt.listen_event(self._mqtt_event,"MQTT_MESSAGE",  wildcard = 'ind/#')

    # mqtt_event['event'] = 'MQTT_MESSAGE'
    # mqtt_event['namespace'] = self.default_mqtt_namespace
    # self.add_event_trigger(mqtt_event)

  def _mqtt_event(self, data):
    self.debug("Event {}", data)
    if not data.topic.startswith('ind/'):
      return

    indicator = data.topic[3:]
    entity_id = 'switch.ind_'+indicator
    state = data.payload.upper()
    if state not in ['ON','OFF']:
      self.warn("Unknown state")
      return

    if not self.entity_exists(entity_id):
      self.warn("Unknown entity {}",entity_id)
      return
    
    service = 'switch/turn_'
    if state == 'ON':
      service += 'on'
    else:
      service += 'off'
    self.hass.call_service(service, entity_id = entity_id)