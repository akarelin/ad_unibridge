import unibridge_base
import json
#from datetime import datetime, time

class MQTTLight(mqtt.AppMqtt):
  def initialize(self):
    try: prefix = self.args["prefix"]
    except: prefix = ''
    try: slug = self.args["slug"]
    except:
      self.log("Slug not provided")
      return
      
    self.topic_prefix = prefix +'light/' + slug
    self.topic_set = self.topic_prefix+'/set'
    self.topic_status = self.topic_prefix
    self.parent = self.get_app(self.args["parent"])
    if not self.parent:
      self.debug("Cannot find {}, got this instead {}", self.args["parent"], self.parent)
      return
    else:
      self.parent.topic = self.topic_status
#    except:
#      trace_log.log("Parent appears to be dead {}", self.parent)
    self.debug("SET Topic {} | STATUS Topic {} | PARENT Topic {}", self.topic_set, self.topic_status, self.parent.topic)
    self.mqtt_listener = self.listen_event(self._mqtt_trigger, "MQTT_MESSAGE")
    # self.discover()

  def terminate(self):
    try:
      self.cancel_listen_event(self.mqtt_listener)
    except:
      pass

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

#
#
#
  def _mqtt_trigger(self, event_name, data, kwargs):
    self.debug("Topic {} Payload {}", data['topic'], data['payload'])
    if data['topic'] != self.topic_set:
      self.debug("Not our Topic {}", data['topic'])
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