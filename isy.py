import unibridge_base
import datetime

class button(hass.AppHass):
  def initialize(self):
    self.debug("Initializing buttons {} to trigger device {}", self.args["buttons"], self.args["entity_id"])
    if isinstance(self.args["buttons"], str):
      self.buttons = [self.args["buttons"]]
    elif isinstance(self.args["buttons"], list):
      self.buttons = self.args["buttons"]
    else:
      self.warn("Buttons are invalid {}", self.args["buttons"])
      return
    self.set_namespace(self.args["namespace"])
    self.listener = self.listen_event(self.cbEvent, "isy994_control")
    self.entity_id = self.args["entity_id"]
  def terminate(self):
    self.cancel_listen_event(self.listener)

  def cbEvent(self, event_name, data, kwargs):
    try:
      command = data['control']
    except:
      command = 'UNKNOWN'
    self.debug("Event {} fired by {}", command, data['entity_id'])
    if data['entity_id'] not in self.buttons:
      self.debug("Not our entity {}", data['entity_id'])
      return
    if command in ['DON']:
      self.debug("Turning on {}", self.entity_id)
      self.turn_on(self.entity_id)
    elif command in ['DOF', 'DFOF']:
      self.debug("Turning off {}", self.entity_id)
      self.turn_off(self.entity_id)
    elif command in ['DFON']:
      self.debug("Turning on full {}", self.entity_id)
      self.turn_on(self.entity_id, brightness = 255)
    else:
      self.debug("Not our command {}", command)
# If its DON, DOFF on any of our buttons - change the status of entity

class indicator(hass.AppHass):
  def initialize(self):
    self.debug("Initializing trigger {} and indicator {}", self.args["trigger"], self.args["indicator"])
    if isinstance(self.args["on_value"], str):
      self.on_value = [self.args["on_value"]]
    elif isinstance(self.args["on_value"], list):
      self.on_value = self.args["on_value"]
    else:
      self.warn("On value is invalid {}", self.args["on_value"])
      return

    self.set_namespace(self.args["trigger_namespace"])
    try:
      self.trigger = self.listen_state(self._trigger,
        self.args["trigger"], duration=60, immediate=True,
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