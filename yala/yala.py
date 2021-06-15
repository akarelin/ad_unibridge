import life
import json
import datetime
import pprint
import math
import appdaemon.adbase as ad
import appdaemon.adapi as adapi
import appdaemon.plugins.hass.hassapi as hass

# region Constants
OFF = 'off'
ON = 'on'
ENTITY_STATES = [ON, OFF]
# endregion

# region Class Primodial
class Primodial:
  api = None
  def __init__(self, env: life.Environment):
    self.api = env.api
    if not self.api:
      raise
# region helpers
  def error(self, msg):
    self.api.error(msg)
  def debug(self, msg):
    self.api.debug(msg)
# endregion
# endregion

# region Class Entity
class Entity(Primodial):
  name = None
  domain = None
  __state = None
# region constructor/destructor
  def __init__(self, name: str, domain: str, env: life.Environment):
    super().__init__(env)
    self.name = name
    self.domain = domain

  @property
  def __str__(self):
    return f"{self.domain}.{self.name}:{self.state}"
# endregion

# region State management
  def update_state(self, new_state):
    self.__state = new_state
  def set_state(self, desired_state):
    raise NotImplemented
  @property
  def state(self):
    return self.__state
# endregion
# endregion

# region Class HassioEntity
class HassioEntity(Entity):
  entity_id = None
  namespace = None

# region Constructor/Destructor
  def __init__(self, env: life.Environment, entity_id: str, namespace: str):
    self.namespace = namespace
    try: domain, entity = entity_id.split('.')
    except:
      self.error(f"Error: Invalid entity {entity_id}")
      return
    self.entity_id = entity_id

    super().__init__(entity, domain, env)
    if not self.api: self.error(f"Unable to connect to AD API")
    if self.api.entity_exists(entity_id, namespace):
      self.__state_callback_handle = self.api.listen_state(self.__callback_state, entity = self.entity, namespace = self.namespace, duration = 30)
    else: self.error(f"Entity {entity_id} does not exist in {namespace{")

  def __del__(self):
    if self.__state_callback_handle: self.api.cancel_listen_state(self.__state_callback_handle)
    super().__del__()

  __state_callback_handle = None
  def __c_state(self, entity, attribute, old, new, **kwargs):
    if entity != self.entity_id or new not in ENTITY_STATES:
      self.error(f"Impossible state {new} of {entity}")
      return
    if new != self.state:
      self.update_state(new)
# endregion

# region State management
  def set_state(self, desired_state):
    if desired_state in ENTITY_STATES:
      self.call_hassio_service(f"turn_{desired_state}")

  def update_state(self, new_state):
    super().update_state(new_state)
# endregion

# region helpers
  def get_hassio_state(self, entity_id = None, namespace = None, **kwargs) -> dict:
    if not entity_id: entity_id = self.entity_id
    if not namespace: namespace = self.namespace
    state = self.api.get_state(entity_id = entity_id, namespace = namespace)
    self.state = state
    self.debug(f"State from hassio {state}")

  def call_hassio_service(self, service, **kwargs):
    self.api(f"homeassistant/{service}", entity_id = self.entity_id, namespace = self.namespace, **kwargs)
# endregion
# endregion

# region Class MQTT Entity
class MqttEntity(Entity):
  base_topic = None
  disco_topic = None
  state_topic = None
  command_topic = None
  mqtt = None

  def __init__(self, env: life.Environment, entity_id: str):
    domain, name = entity_id.split('.')
    super().__init__(name, domain, env)
    self.mqtt = env.mqtt

    self.base_topic = "/".join([domain, name])
    self.state_topic = "/".join([self.base_topic, "state"])
    self.command_topic = "/".join([self.base_topic, "set"])
    self.disco_topic = "/".join(["homeassistant", domain, name])

    self.api.listen_event(self.__c_mqtt_command, topic=self.command_topic)
  
  def __discover(self):
    raise NotImplemented

  def publish(self):
    payload = {"state": self.state}
    self.mqtt.mqtt_publish(self.state_topic, payload = json.dumps(payload))

  def __c_mqtt_command(self, event_name, data, kwargs):
    if "payload" not in data:
      self.error(f"Invalid payload {pprint.pformat(data)}")
      return
    payload = json.loads(data["payload"])
    command = payload.get("state").lower()
    if self.domain == 'switch' and command in ['on','off']:
      self.set_state(command)
    else:
      self.error(f"Invalid command {command}")

  



# region Class Indicator
INDICATOR_PARAMETERS = ['entity', 'name', 'namespace', 'type']

class Indicator(Entity):
  __indicate = None

  def __init__(self, entity, indicate: Entity, env: life.Environment):
    super().__init__(d, env)
    self.__indicate = indicate

  def refresh(self, force = False):
    desired_state = self.__indicate.state
    state = self.state
    if state != desired_state:
      if state in ENTITY_STATES:
        self.call_hassio_service(f"turn_{state}")
      else:
        self.__error(f"Impossible desired state {desired_state}")
# endregion