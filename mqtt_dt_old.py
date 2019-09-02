import json
import unibridge
#from datetime import datetime, time

class device_tracker(unibridge.AppMqtt):
  def initialize(self):
    try: self.topic = self.args["topic"]
    except: self.topic = "unifi/+/status/wifi/+/client/+"
    self.set_namespace(self.args['namespace'])

    self.sites = {}
    try: self.sites = self.args["sites"]
    except:
      self.warn("Sites are invalid {}", self.args["sites"])
      return

    self.devices = {}
    try: self.devices = self.args["devices"]
    except:
      self.warn("Devices are invalid {}", self.args["devices"])
      return

    self.debug("~~~~ Devices {}", self.devices)
    self.debug("~~~~ Sites {}", self.sites)
    self.mqtt_subscribe(self.topic)
    self.mqtt_listener = self.listen_event(self._mqtt_trigger, "MQTT_MESSAGE")
    
  def terminate(self):
    try:
      self.mqtt_unsubscribe(self.topic)
      self.cancel_listen_event(self.mqtt_listener)
    except:
      pass

  def _mqtt_trigger(self, event_name, data, kwargs):
    self.debug("Topic {} Payload {}", data['topic'], data['payload'])
    try:
      payload = json.loads(data['payload'])
      site = data['topic'].split('/')[1]
      ap = data['topic'].split('/')[4]
      name = data['topic'].split('/')[6]
      val = payload['val']
      mac = payload['mac']
      ts = payload['ts']
    except:
      self.debug("Not for us")
      return

#    if not val:
#      self.debug("~~~~~~ {} Not here", name)
      return
   
    try:
      device = self.devices[mac]
      self.debug("~~~~~ {} Our Device", device)
    except:
      self.debug("~~~~~ {} Not our device", mac)
      return

    location = {}
    try:
      location = self.sites[site]
      self.debug("~~~~~ {} Our location", location)
    except:
      self.debug("~~~~~ {} Not our site", site)
      return

    topic = 'device/'+device
    payload = location
    self.debug("~~~~~~~ {} => {}", topic, payload)
    self.mqtt_publish(topic, payload, qos = 0, retain = False)

    # if data['payload'] in ['ON','OFF']:
    #   light['state']=data['payload']
    #   self.debug("Binary state {}", state)
    # else:
    #   try:
    #     payload = json.loads(data['payload'])
    #     payload['state']=payload['state'].upper()
    #     self.debug("JSON payload {}", payload)
    #     light = payload
    #   except:
    #     self.debug("Invalid Payload {}", data['payload'])
    #     return
    # self.json_light(light)

#     try: prefix = self.args["prefix"]
#     except: prefix = ''
#     try: slug = self.args["slug"]
#     except:
#       self.log("Slug not provided")
#       return
      
#     self.topic_prefix = prefix +'light/' + slug
#     self.topic_set = self.topic_prefix+'/set'
#     self.topic_status = self.topic_prefix
#     self.parent = self.get_app(self.args["parent"])
#     if not self.parent:
#       self.debug("Cannot find {}, got this instead {}", self.args["parent"], self.parent)
#       return
#     else:
#       self.parent.topic = self.topic_status
# #    except:
# #      trace_log.log("Parent appears to be dead {}", self.parent)
#     self.debug("SET Topic {} | STATUS Topic {} | PARENT Topic {}", self.topic_set, self.topic_status, self.parent.topic)
#     self.mqtt_listener = self.listen_event(self._mqtt_trigger, "MQTT_MESSAGE")
#     # self.discover()

#   def terminate(self):
#     try:
#       self.cancel_listen_event(self.mqtt_listener)
#     except:
#       pass

#   # def discover(self):
#   #   self.log("Discovery Publishing")
#   #   config = {}
#   #   config['name'] = self.args["name"]
#   #   config['uniq_id'] = "light."+self.args["slug"]

#   #   config['schema'] = 'json'
#   #   config['brightness'] = True
#   #   config['command_topic'] = self.topic_set
#   #   config['state_topic'] = self.topic_status
#   #   config_json = json.dumps(config)
#   #   self.l("Publishing config {}", config_json)
#   #   self.log(config_json)
#   #   self.mqtt_publish(self.topic_prefix+'/config', config_json)
    
#   def json_light(self, light):
#     self.debug('JSON Light {}', light)
    
#     if light['state'] == 'ON':
#       self.debug("Processing ON {}", light)
#     elif light['state'] == 'OFF':
#       self.debug("Processing OFF {}", light)
#       self.parent.light_off()
#       return
#     else:
#       self.log("Unknown state {}", state)
#       return

#     try:
#       brightness = int(light['brightness'])
#       self.debug("Setting brightness to {}", brightness)
#     except:
#       brightness = None
#       self.debug("Default Brightness")

#     if brightness is None:
#       self.parent.light_on()
#     else:
#       self.parent.light_on(brightness)

# #
# #
# #
#   def _mqtt_trigger(self, event_name, data, kwargs):
#     self.debug("Topic {} Payload {}", data['topic'], data['payload'])
#     if data['topic'] != self.topic_set:
#       self.debug("Not our Topic {}", data['topic'])
#       return

#     if data['payload'] in ['ON','OFF']:
#       light['state']=data['payload']
#       self.debug("Binary state {}", state)
#     else:
#       try:
#         payload = json.loads(data['payload'])
#         payload['state']=payload['state'].upper()
#         self.debug("JSON payload {}", payload)
#         light = payload
#       except:
#         self.debug("Invalid Payload {}", data['payload'])
#         return
#     self.json_light(light)

#     # try:
#     #   self.json = json.loads(data['payload'])
#     # except:
#     #   self.json = Null
#     #   if(data['payload'] in ['ON','OFF']):
#     #     self.

    
#     #   if()
      
    

# #    self.mqtt_subscribe("#")
# #    self.log("MQTTListener: Initializing")
# #  def hassLink(self, Hass):
# #    self.hass = Hass


# # class HassListener(hass.Hass):
# #   def initialize(self):
# #     self.set_namespace(self.args["namespace"])
# #     self.log("HassListener: Initializing")
# #     self.mqtt = self.get_app(self.args["mqtt_listener"])
    
    
    
# #    self.mqtt.subscribe('light/colorloop')

# #    self.mqtt.hassLink(self)
# #    self.log("HassListener: Initialized")
# #    self.handle_event_listener = self.listen_event(self._mqtt_event)
 
# #  def terminate(self):
# #    self.cancel_listen_event(self.handle_event_listener)#

# #  def _mqtt_event(self, event_name, data, kwargs):
# #    self.log("Event {} fired with data {}".format(event_name, data))

# # class lightHASS(hass.Hass):
  
# #   def initialize(self, event_name, data, kwargs):
# #     self.log("Initializing HASS with data {}".format(data))

# #class colorloop2(mqtt.Mqtt, hass.Hass):
# #class colorloop2(hass.Hass, mqtt.Mqtt):

# #  def initialize(self):
# #    self.log("INIT")
# #    self.set_namespace(self.args["namespace"])
# #    mqtt_handle = self.mqtt_subscribe(self._mqtt, topic = self.args["mqtt_topic"])

# #    self.set_namespace(self.args["namespace"])
# #    self.log("!!!!! {} {}".format(self.args["entity_id"],self.args["namespace"]))
# #    self.hass_handle = hass.listen_state(namespace=self.args["namespace"], cb = self._hass_state, entity = self.args["entity_id"], attribute="All" )
# #    self.debugimer = self.run_every(self._timer, self.datetime(), self.args["precision"])

# #  def terminate(self):
# #    self.cancel_listen_state(self.hass_handle)
# #    self.cancel_timer(self.debugimer)

# #  def _hass_state(self, entity, attribute, old, new, kwargs):
# #    self.publish()
# #    self.log("TRIGGERED {}".format(entity))
  
# #  def _timer(self, kwargs):
# #    state = self.get_state(self.args["entity_id"],attribute="hs_color",namespace=self.args["namespace"])
# #    self.publish()
# #    self.log("TIMER {}".format(state))
    
# #  def publish(self):
# #    state = self.get_state(self.args["entity_id"],attribute="all",namespace=self.args["namespace"])
# #    self.log("Publishing {}".format(repr(state)))
# #    self.mqtt_publish(self, self.args["topic"], state)


#   # def _mqtt(self, kwargs):
#   #   self.log("MQTT {}".format(kwargs))

#   # def _timer(self, kwargs):
#   #   self.log("Timer")
#   #   self.updateIndicator()
# # class colorloop2mqtt(mqtt.Mqtt):

# #   def initialize(self):
# #     self.mqtt_subscribe(

# #   module: hue
# #   class: colorloop2
# #   entities:
# #     - light.hue_corner
# #   period: 60
# #   precision: 5
# #   brightness: 32
# #   brightness_control: input_number.colorloop_brightness
# #   namespace: sway_hassio
# #   mqtt_topic: /sway/light/colorloop