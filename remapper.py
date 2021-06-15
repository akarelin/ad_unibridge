import u3
import json
import datetime

import telnetlib

"""
remapper i2 btn:
  module: remapper
  class: Remapper

  base_topic: atlona
"""

class Remapper(u3.U3Base):

  def initialize(self):
    super().initialize()
    self.debug(f"Initialized remapper {self.args}")

  def _mqtt_callback(self, event_name, data, kwargs):
    topic = data.get('topic')
    payload = data.get('payload')
    self.debug("Callback {} {}", output, device)

  def trigger(self, kwargs):
    pass

