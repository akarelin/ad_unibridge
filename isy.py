import appdaemon.plugins.hass.hassapi as hass
import datetime

class button(hass.Hass):
  def l(self, message, *args):
    try: debug = self.args["debug"]
    except: debug = False
    if debug: self.log(message.format(*args))

  def initialize(self):
    self.l("Initializing buttons {} to trigger device {}", self.args["buttons"], self.args["entity_id"])
    if isinstance(self.args["buttons"], str):
      self.buttons = [self.args["buttons"]]
    elif isinstance(self.args["buttons"], list):
      self.buttons = self.args["buttons"]
    else:
      self.l("Buttons are invalid {}", self.args["buttons"])
      return
    self.set_namespace(self.args["namespace"])
    self.listener = self.listen_event(self.cbEvent, "isy994_control")#, "isy994_control")
    self.entity_id = self.args["entity_id"]
  def terminate(self):
    self.cancel_listen_event(self.listener)

  def cbEvent(self, event_name, data, kwargs):
    try:
      command = data['control']
    except:
      command = 'UNKNOWN'
    self.l("Event {} fired by {}", command, data['entity_id'])
    if data['entity_id'] not in self.buttons:
      self.l("Not our entity {}", data['entity_id'])
      return
    if command in ['DON']:
      self.l("Turning on {}", self.entity_id)
      self.turn_on(self.entity_id)
    elif command in ['DOF', 'DFOF']:
      self.l("Turning off {}", self.entity_id)
      self.turn_off(self.entity_id)
    elif command in ['DFON']:
      self.l("Turning on full {}", self.entity_id)
      self.turn_on(self.entity_id, brightness = 255)
    else:
      self.l("Not our command {}", command)
# If its DON, DOFF on any of our buttons - change the status of entity

class indicator(hass.Hass):
  def l(self, message, *args):
    try: debug = self.args["debug"]
    except: debug = False
    if debug: self.log(message.format(*args))

  def initialize(self):
    self.l("Initializing trigger {} and indicator {}", self.args["trigger"], self.args["indicator"])
    
    if isinstance(self.args["on_value"], str):
      self.on_value = [self.args["on_value"]]
    elif isinstance(self.args["on_value"], list):
      self.on_value = self.args["on_value"]
    else:
      self.log("On value is invalid {}", self.args["on_value"])
      return

    self.set_namespace(self.args["trigger_namespace"])
    self.trigger = self.listen_state(self._trigger,
      self.args["trigger"], duration=60, immediate=True,
      namespace=self.args["trigger_namespace"])
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
    self.l("Trigger changed to {}", new)
    self.updateIndicator()

  def _indicator(self, entity, attribute, old, new, kwargs):
    self.l("Indicator changed to {}", new)
    self.updateIndicator()
  
  def _timer(self, kwargs):
    self.l("Timer")
    self.updateIndicator()

  def updateIndicator(self):
    self.l("Starting with {} and {}", self.args["trigger"], self.args["indicator"])    
    trigger_state = self.get_state(self.args["trigger"], namespace=self.args["trigger_namespace"])
    self.l("Trigger state {}", repr(trigger_state))
    indicator_state = self.get_state(self.args["indicator"], namespace=self.args["indicator_namespace"])
    self.l("Indicator state {}", repr(indicator_state))
    
    if trigger_state in self.on_value and indicator_state == 'off':
      self.l("Turning indicator {} on", self.args["indicator"])
      self.turn_on(self.args["indicator"], namespace = self.args["indicator_namespace"])
    elif trigger_state not in self.on_value and indicator_state != 'off':
      self.l("Turning indicator {} off", self.args["indicator"])
      self.turn_off(self.args["indicator"], namespace = self.args["indicator_namespace"])
    else:
      self.l("Not changing  indicator {}", self.args["indicator"])