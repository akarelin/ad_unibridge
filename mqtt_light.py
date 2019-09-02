import unibridge
import json
#from datetime import datetime, time

class mqtt_light(unibridge.AppMqtt):
  def initialize(self):
    self.parent = self.get_app(self.args["parent"])
    self.set_namespace(self.parent.args["mqtt_namespace"])

    topic = 'light/' + self.parent.args["topic"]
    self.parent.topic_set = topic+'/set'
    self.parent.topic_state = topic+'/state'

    self.debug("SET Topic {} | STATUS Topic {}", self.parent.topic_set, self.parent.topic_state)
    self.mqtt_listener = self.listen_event(self._mqtt_trigger, "MQTT_MESSAGE")
    # self.discover()

  def terminate(self):
    try:
      self.cancel_listen_event(self.mqtt_listener)
    except:
      pass

  def json_light(self, light):
    self.debug('JSON Light {}', light)
    
    if light['state'] == 'ON':
      self.debug("Processing ON {}", light)
    elif light['state'] == 'OFF':
      self.debug("Processing OFF {}", light)
      self.parent.light_off()
      return
    else:
      self.log("Unknown state {}", state)
      return

    try:
      brightness = int(light['brightness'])
      self.debug("Setting brightness to {}", brightness)
    except:
      brightness = None
      self.debug("Default Brightness")

    if brightness is None:
      self.parent.light_on()
    else:
      self.parent.light_on(brightness)

  def _mqtt_trigger(self, event_name, data, kwargs):
    self.debug("Topic {} Payload {}", data['topic'], data['payload'])
    if data['topic'] != self.parent.topic_set:
#      self.debug("Not our Topic {}", data['topic'])
      return

    if data['payload'] in ['ON','OFF']:
      light['state']=data['payload']
      self.debug("Binary state {}", state)
    else:
      try:
        payload = json.loads(data['payload'])
        payload['state']=payload['state'].upper()
        self.debug("JSON payload {}", payload)
        light = payload
      except:
        self.debug("Invalid Payload {}", data['payload'])
        return
    self.json_light(light)

  # def discover(self):
  #   self.log("Discovery Publishing")
  #   config = {}
  #   config['name'] = self.args["name"]
  #   config['uniq_id'] = "light."+self.args["slug"]

  #   config['schema'] = 'json'
  #   config['brightness'] = True
  #   config['command_topic'] = self.topic_set
  #   config['state_topic'] = self.topic_status
  #   config_json = json.dumps(config)
  #   self.l("Publishing config {}", config_json)
  #   self.log(config_json)
  #   self.mqtt_publish(self.topic_prefix+'/config', config_json)
    
