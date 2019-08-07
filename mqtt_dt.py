import appdaemon.plugins.mqtt.mqttapi as mqtt
import json

class MQTT_DT(hass.Hass):
  def _log(self, level, message, *args):
    try:
      if args: self.log(message.format(*args), level=level)
      else: self.log(message, level=level)
    except:
      self.log("Debug Logger Failed {}".format(message))
  def warn(self, message, *args):
    level = "WARN"
    self._log(level, message, *args)
  def debug(self, message, *args):
    level = "INFO"
    enabled = False
    try: 
      if self.args["debug"] == True:
        enabled = True
    except: 
      pass
    if not enabled: 
      return
    self._log(level, message, *args)

  def initialize(self):
    self.debug("Initializing trigger {} and indicator {}", self.args["trigger"], self.args["indicator"])
    if isinstance(self.args["prefix"], str):
      self.prefix = [self.args["prefix"]] + '_'
    else:
      self.warn("Prefix is invalid {}", self.args["prefix"])
      return
#    if isinstance(self.args["prefix"], str):
#      self.prefix = [self.args["prefix"]]


#    elif isinstance(self.args["prefix"], list):
#      self.on_value = self.args["prefix"]
#    else:
#      self.warn("On value is invalid {}", self.args["prefix"])
#      return
        
    self.trackers = []
    trackers = self.get_state('device_tracker', namespace=self.args["device_namespace"])
    for tracker in trackers:
        entity_id = tracker.entity_id
      if entity_id.startswith(self.prefix):
          name=tracker.entity_id.split(self.prefix)[1]
          user=name.split('_')[0]
          device=name.split('_')[1]
          self.trackers += {'name':name, 'user':user, 'device':device, 'entity_id':entity_id}

    self.set_namespace(self.args["tracker_namespace"])
    try:
      self.trigger = self.listen_state(self._trigger,
        self.trackers, duration=60, immediate=True,
        namespace=self.args["trigger_namespace"])
    except:
      self.warn("Listener for trigger {} failed", self.args["trigger"])
      return

    self.indicator = self.listen_state(self._indicator,
      self.args["indicator"],
      duration=60, immediate=True,
      namespace=self.args["indicator_namespace"])
    runtime = datetime.time(0, 0, 0)
    self.timer = self.run_minutely(self._timer, runtime)
    self.updateIndicator()

  def terminate(self):
    self.cancel_listen_state(self.trigger)
    self.cancel_listen_state(self.indicator)
    self.cancel_timer(self.timer)

  def _trigger(self, entity, attribute, old, new, kwargs):
    self.debug("Trigger changed to {}", new)
    self.updateIndicator()

  def _indicator(self, entity, attribute, old, new, kwargs):
    self.debug("Indicator changed to {}", new)
    self.updateIndicator()
  
  def _timer(self, kwargs):
    self.debug("Timer")
    self.updateIndicator()

  def updateIndicator(self):
    self.debug("Starting with {} and {}", self.args["trigger"], self.args["indicator"])    
    trigger_state = self.get_state(self.args["trigger"], namespace=self.args["trigger_namespace"])
    self.debug("Trigger state {}", repr(trigger_state))
    indicator_state = self.get_state(self.args["indicator"], namespace=self.args["indicator_namespace"])
    self.debug("Indicator state {}", repr(indicator_state))
    
    if trigger_state in self.on_value and indicator_state == 'off':
      self.log("Turning indicator {} on".format(self.args["indicator"]))
      self.turn_on(self.args["indicator"], namespace = self.args["indicator_namespace"])
    elif trigger_state not in self.on_value and indicator_state != 'off':
      self.log("Turning indicator {} off".format(self.args["indicator"]))
      self.turn_off(self.args["indicator"], namespace = self.args["indicator_namespace"])
    else:
      self.debug("Not changing indicator {}", self.args["indicator"])


  def _log(self, level, message, *args):
    try:
      if args: self.log(message.format(*args), level=level)
      else: self.log(message, level=level)
    except:
      self.log("Debug Logger Failed {}".format(message))
  def warn(self, message, *args):
    level = "WARN"
    self._log(level, const_warn_level, message, *args)
  def debug(self, message, *args):
    level = "INFO"
    enabled = False
    try: 
      if self.args["debug"] == True:
        enabled = True
    except: 
      pass
    if not enabled: 
      return
    self._log(level, message, *args)

  def initialize(self):
    try: prefix = self.args["prefix"]
    except: prefix = 'device_tracker.unifi_'
    # try: slug = self.args["slug"]
    # except:
    #   self.log("Slug not provided")
    #   return
   
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