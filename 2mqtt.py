import u3
import json
import datetime

"""
remapper:
  module: 2mqtt
  class: event2MQTT
  debug: True
  default_namespace: deuce

  triggers:
    - type: event
"""

class ToMQTT(u3.U3Base):
  def initialize(self):
    super().initialize()
    self.debug(f"Initialized remapper {self.args}")

  def _mqtt_callback(self, event_name, data, kwargs):
    topic = data.get('topic')
    payload = data.get('payload')
    self.debug(f"Callback {topic} {payload}")

  def trigger(self, kwargs):
    pass

