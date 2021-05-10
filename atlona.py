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

class Atlona(unibridge.MqttApp):
  address = None
  input_names = {}
  inputs = []
  outputs = {"HDMI": None, "HDBT": None}
  devices = []
  all_devices = []
  tn = None

  def initialize(self):
    super().initialize()
    self.address = self.args.get('address')
    self.input_names = self.args.get('input_names')
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
    self.outputs['HDMI'] = self.inputs[self.get_input(1)].get('device')
    self.outputs['HDBT'] = self.inputs[self.get_input(0)].get('device')
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
    if output in [1,'HDMI']:
      out_index = 1
    elif output in [0,'HDBT']:
      out_index = 0
    else:
      self.error("Invalid output {}", output)
      return
    
    if device not in self.devices:
      self.error("Invalid device {}", device)
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

      i['device'] = self.input_names.get(name)
      self.inputs.append(i)
  def send_command(self, cmd, timeout = 30):
    self._start()
    result = self._cmd(cmd, timeout = timeout)
    self._end()
    return result

  # endregion

  # region Telnet
  def _start(self):
    self.tn = telnetlib.Telnet(self.address)
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

AVA_TN_TIMEOUT = 10
class AVAccess(unibridge.MqttApp):
  address = None
  prefix = None
  inputs = []
  outputs = []
  mp = [None, None, None, None]
  tn = None

  def initialize(self):
    super().initialize()
    self.address = self.args.get('address')
    self.inputs = self.args.get('inputs')
    self.outputs = self.args.get('outputs')
    self.prefix = self.args.get('prefix')
    self.debug(f"AVAccess matrix initialized\n    {self.address}  {self.prefix}\n    {self.inputs}\n    {self.outputs}\n")
    self.refresh()
    
    self.debug(f"  +-- Subscribing to control events")
    self.mqtt.mqtt_subscribe(f"{self.prefix}/output/+/set")
    self.mqtt.listen_event(self._mqtt_callback, "MQTT_MESSAGE", wildcard = f"{self.prefix}/output/#")
    self.debug(f"  +-- Initialization Completed")

  # region SETs
  def _mqtt_callback(self, event_name, data, kwargs):
    topic = data.get('topic')
    payload = data.get('payload')
    output = topic.split('/')[2]
    device = payload
    self.debug(f" *** Callback {output} {device}")
    self.set_output(output, device)

  def trigger(self, kwargs):
    self.refresh()

  def set_output(self, output, input):
    try:
      i_output = self.outputs.index(output) + 1
      i_input = self.inputs.index(input) + 1
    except:
      self.error(f"Unknown IO {output} {input}")
      return
    cmd = f"SET SW hdmiin{i_input} hdmiout{out_index}"
    self.debug(f"Sending command {cmd}")
    result = self.send_command(cmd)
    self.debug(f"Result {result}")
    self.refresh()
  # endregion

  # region GETs
  def refresh(self):
    self.debug(f"Refresh Starting")
    self.query()
    self.debug(f"        Queried")
    self.publish()
    self.debug(f"        Published")

  def query(self):
    self.get_mp()

  def publish(self):
    mphr = self.mphr
    self.mqtt.mqtt_publish(f"{self.prefix}/state", json.dumps(self.mphr))
    for o_index, i_index in enumerate(mp):
      self.mqtt.mqtt_publish(f"{self.prefix}/output/{o_index+1}/state", i_index)

  @property
  def mphr(self):
    result = {}
    for o_index, o in enumerate(outputs):
      i = inputs[mp[o_index-1]]
      result[o] = i
    return result

  def get_mp(self):
    result = self.send_command("GET MP all")
    self.debug(f"MPs: {result}")
    for mp in result:
      i_index = int(mp.split(" ")[1][-1])
      o_index = int(mp.split(" ")[2][-1])
      mp[o_index] = i_index
    self.debug(f"    Parsed: {mp}")
  # endregion

  # region Telnet
  def send_command(self, cmd):
    self._start()
    result = self._cmd(cmd)
    self._end()
    return result

  def _start(self):
    self.debug(f"Connecting to {self.address}:23 TO={AVA_TN_TIMEOUT}")
    self.tn = telnetlib.Telnet(self.address, 23, AVA_TN_TIMEOUT)
    self.debug(f"Connected to {self.address} handle={self.tn}")
    welcome = self.tn.read_until(b"\n\r")
    self.debug(f"Welcome {welcome}")

  def _end(self):
    self.tn.close()

  def _cmd(self, cmd):
    self.debug(f"CMD start {cmd}")
    bcmd = cmd.encode('ascii')
    self.tn.write(bcmd)
    #raw = self.tn.read(b"\n\r", timeout)
    self.debug(f"    written to buffer")
    result = self.tn.read_all().splitlines()
    #  response = raw.decode('ascii').split('\n#')[0]
    self.debug(f"    Result {result}")
    return result
  # endregion