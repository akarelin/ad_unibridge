import unibridge
import json
import datetime

import telnetlib

"""
atlona:
  module: atlona
  class: Atlona

  base_topic: atlona
"""

INPUTS = {
#    'USB-C': 'USB-C',
    "DisplayPort":  "AlexPC",
    "HDMI 3": "CCTV",
    "HDMI 4": "NVR",
#    'BYOD': 'BYOD'
}

class Atlona(unibridge.MqttApp):
  inputs = []
  outputs = {"HDMI": None, "HDBT": None}
  devices = []
  all_devices = []
  tn = None

  def initialize(self):
    super().initialize()
    self.refresh()
    
    self.mqtt.mqtt_subscribe('atlona/output/+/set')
    self.mqtt.listen_event(self._mqtt_callback, "MQTT_MESSAGE", wildcard = 'atlona/output/#')

  def _mqtt_callback(self, event_name, data, kwargs):
    topic = data.get('topic')
    payload = data.get('payload')
    output = topic.split('/')[2]
    device = payload
    self.debug("Callback {} {}", output, device)
    self.set_output(output, device)

  def refresh(self):
    self.query()
    self.publish()

  def query(self):
    self._start()
    self.get_input_states()
    self.outputs['HDMI'] = self.inputs[self.get_input(0)].get('device')
    self.outputs['HDBT'] = self.inputs[self.get_input(1)].get('device')
    self.devices = []
    for i in self.inputs:
      d = i.get('device')
      self.all_devices.append(d)
      state = i.get('state')
      if state and d:
        self.devices.append(d)

    self.debug("\n\tInputs: {} \n\tOutputs: {}\n\tDevices: {}",self.inputs, self.outputs, self.devices)
    self._end()
  
  def publish(self):
    state = {}
    state['outputs'] = json.dumps(self.outputs)
    state['devices'] = json.dumps(self.devices)
    state['inputs'] = json.dumps(self.inputs)
    state['HDMI'] = self.outputs['HDMI']
    state['HDBT'] = self.outputs['HDBT']

    self.mqtt.mqtt_publish("atlona/state", json.dumps(state))
    self.mqtt.mqtt_publish("atlona/state/devices", json.dumps(self.devices))
    self.mqtt.mqtt_publish("atlona/state/outputs", json.dumps(self.outputs))
    self.mqtt.mqtt_publish("atlona/state/output/hdmi", self.outputs['HDMI'])
    self.mqtt.mqtt_publish("atlona/state/output/hdbt", self.outputs['HDBT'])
    
  def trigger(self, kwargs):
    self.refresh()

  def set_output(self, output, device):
    out_index = int(output)
    if out_index not in [0,1]:
      self.error("Invalud output {}", output)
      return
    
    if device not in self.devices:
      self.error("Invalud device {}", device)
    dev_index = self.all_devices.index(device)

    cmd = f"Display:Matrix:Set {dev_index} {out_index}"
    self.debug(cmd)
    self.send_command(cmd)
    self.refresh()

# region Internals
  def get_input(self, i):
    hr = self._cmd(f"Display:Matrix:Get {i}")
    result = None
    try:
      result = int(hr.split('input = ')[1])
    except:
      self.warn("Unable to parse {}", hr)
    return result

  def get_input_states(self):
    self.inputs = []
    i = {}
    parsed = {}

    raw = self._cmd("GetInputStates", timeout=30)
    raw = raw.replace('[','').replace(']','')
    for v in raw.split(', '):
      i = {}
      name, state = v.split(': ')
      i['name'] = name
      i['state'] = bool(state)
#      self.debug("INPUTS {} {} {}",INPUTS, name, INPUTS.get(name))

      i['device'] = INPUTS.get(name)
#      self.debug("\n{}", i)
      self.inputs.append(i)
#    self.debug("Inputs: {}", self.inputs)
  def send_command(self, cmd, timeout = 30):
    self._start()
    result = self._cmd(cmd, timeout = timeout)
    self._end()
    return result

# endregion

# region Telnet
  def _start(self):
    self.tn = telnetlib.Telnet('10.172.2.81')
    a = self.tn.read_until(b"\n\n", 3)
    self.tn.write(b"OutputMode h\n")
    a = self.tn.read_until(b"#\n", 3)
  
  def _end(self):
    self.tn.close()

  def _cmd(self, cmd, timeout = 3):
    if cmd[-1] != '\n':
      cmd += '\n'
    bcmd = cmd.encode('ascii')
    self.tn.write(bcmd)
    raw = self.tn.read_until(b"#\n", timeout)
    response = raw.decode('ascii').split('\n#')[0]
    self.debug("Raw {} Parsed {}", raw, response)
    return response

  def _parse_input(self, hr):
    i = 0
    result = None
    try:
      i = int(hr.split('input = ')[1])
      result = INPUTS[i]
    except:
      self.warn("Unable to parse {}", hr)
    return result
# endregion