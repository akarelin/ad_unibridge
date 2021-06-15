import unibridge

"""
ao:
  module: av
  class: av

  activities:
    Off
    In:AppleTV
    In:HTPC
    In:Atlona
    Pause
    VolUp
    VolDn
    Out:Speakers
    Out:Headphones
    TV:On
    TV:Off
    Monitor:Off
    Monitor:Default
  sources:
    - type: apple_tv
      media_player: media_player.ao_appletv
      display_input: 'AppleTV'
    - type: atlona
      display_input: 'Receiver'
      receiver_input: 'Atlona'
    - type: Generic
      name: HTPC
      display_input: 'eVGA'
  tv:
    type: LG
  monitor:
    type: PowerSwitch
  audio:
    - type: Headphones
    - type: Speakers
"""
# region Rooms

LGTV = 'lgtv'
PS = 'power_switch'
DENON = 'denon'
APPLE_TV = 'appletv'

class AV(unibridge.MqttApp):
  default_namespace = None
#
# States
#
  tv = {}
  monitor = {}
  receiver = {}
  sources = {}
#
# Configuration
#
  devices = {}

  def initialize(self):
    super().initialize()
    self.default_namespace = "seven"
    # self.hass = self.get_plugin_api("seven")
    # self.hasses['seven'] = self.get_plugin_api("seven")
    # self.hasses['ao'] = self.get_plugin_api("ao")
    # self.hasses['deuce'] = self.get_plugin_api("deuce")


    tv = {}
    tv['entity_id'] = "media_player.ao_tv"
    tv['type'] = TV_LG
    devices['tv'] = {"entity_id": "media_player.ao_tv", "type": LGTV, "namespace": "ao" }
    devices['monitor'] = {"entity_id": "switch.ao_monitor_power", "type": PS, "namespace": "ao" }
    devices['receiver'] = {"entity_id": "media_player.ao_receiver", "type": DENON, "namespace": "ao" }
    devices['appletv'] = {"entity_id": "media_player.ao_appletv", "type": APPLE_TV, "namespace": "ao" }
    for d in devices:
      self.update_state(d)
    

  def update_state(self, d):
    device = devices.get(d)
    namespace = device.get('namespace',self.default_namespace)
    e = device.get('entity_id')
    state = self.api.get_state(entity_id = e, attribute = all, namespace = namespace)
    if d == 'tv': self.tv = state
    elif d == 'monitor': self.monitor = state
    elif d == 'receiver': self.receiver = state
    else self.sources[d] = state
  
  def source_select(self, source = NONE, display = TV, audio = NONE):
    if source == 'appletv':
      self.device_on(source)

    if display:
      self.device_on(display)
    else:
      self.device_off(TV)
    
    if audio in [NONE,HP]:
      self.device_off(RECEIVER)
      self.display_audio(audio)
    elif audio == SPEAKERS:
      self.device_on(RECEIVER)
      self.display_audio(audio)

        


  def off(self, devices = []):
  def device_on(self, device):

  def source(self, source = None, display = TV, audio = NONE):
    self.device_on(display)
    if audio == SPEAKERS:
      self.device_on(self.receiver)
    elif audio in [HP,NONE]:
      self.device_off(self.receiver)
    
    self.source_select(display = display, audio = audio)
  
  def source_select(self, source = NONE, display = TV, audio = NONE):

    self.display_on(display)
    if audio == SPEAKERS:
      self.device_on(self.receiver)
    elif audio in [HP,NONE]:
      self.device_off(self.receiver)


    
    
    
    

    state = "Room: {}\n\tOutputs: {}\n\tInputs: {}\n\tActions: {}\n\tButtons: {}".format(ROOM, OUTPUTS, INPUTS, ACTIONS, BUTTONS)
    hass.services.call("notify", "debug_av", {'message': state}, False)
    if ROOM:
      logger.info("\n\tAV.PY Called with %s", data)
      action = data.get("action")

        if action == 'Button':
            Button(data.get("button"), data.get("cmd"))
        else: 
            Action(action)


    def Command(command):
        logger.info("Command: %s", command)
        sc = command
        cmd = sc.pop('cmd')
        domain = ""
        if '.' in cmd:
            domain, service = cmd.split('.')
        else:
            domain = sc.get('entity_id').split('.')[0]
            service = cmd
        logger.info("%s => %s (%s)", domain, service, sc)
        hass.services.call(domain, service, sc, False)

    def Action(action, sequence = ACTIONS):
        logger.info("Action: %s", action)

        if action in sequence:
            calls = sequence[action]
        else:
            logger.error("Unknown Action %s", action)
            return
        logger.info("\n\tCalls: %s", calls)
        for c in calls:
            Command(c)

    def Button(btn, cmd):
        action = None
        if btn in BUTTONS.keys():
            a = BUTTONS[btn]
            try: action = a[cmd]
            except: action = a
            Action(action)
            return
        elif btn in ['volup','voldn']:
            if cmd == 'FON':
                Output('Speakers')
            elif cmd == 'FOF':
                Output('None')
            elif cmd == 'ON':
                Volume('VolUp')
            elif cmd == 'OF':
                Volume('VolDn')
        else:
            logger.error("Unknown button %s command %s", btn, cmd)

    def Output(action):
        Action(action, sequence = OUTPUTS)

    def Volume(cmd):
        v20 = 0
        i = 0
        try:
            v20 = int(hass.states.get(AV).attributes.volume_level)*20
        except:
            logger.error("Unable to determine %s volume", AV)
            return
        if cmd == 'VolUp': i = 2
        new_volume = int((v20-1 + i)/20)
        hass.services.call("media_player", 'volume_set', {"entity_id": AV, "volume_level": new_volume}, False)

# region void main(void)
# endregion


    # self.mqtt.mqtt_subscribe('atlona/output/+/set')
    # self.mqtt.listen_event(self._mqtt_callback, "MQTT_MESSAGE", wildcard = 'atlona/output/#')

#   def _mqtt_callback(self, event_name, data, kwargs):
#     topic = data.get('topic')
#     payload = data.get('payload')
#     output = topic.split('/')[2]
#     device = payload
#     self.debug("Callback {} {}", output, device)
#     self.set_output(output, device)


def Room():
    ao_tv = hass.states.get("media_player.ao_tv")
    fr_tv = hass.states.get("media_player.fr_tv")
    if not fr_tv: return 'ao'
    elif fr_tv: return 'fr'
    else: return None
ROOM = Room()
if not ROOM:
    logger.error("Not a room")
    exit()
# endregion
# region Global commands
ATV = 'media_player.'+ROOM+"_appletv"
ATVR = 'remote.'+ROOM+"_appletv"
TV = 'media_player.'+ROOM+"_tv"
AV = 'media_player.'+ROOM+'_receiver'
OUT_SELECTOR = 'input_select.'+ROOM+'_av_output'
PAUSE = [{"cmd": "media_player.media_play_pause", "entity_id": ATV}]

if ROOM == 'ao':
    TV2_POWER = 'switch.ao_monitor_power'
elif ROOM == 'fr':
    TV2_POWER = 'switch.kitchen_tv_power'

AV_ON = [{"cmd": 'turn_on', "entity_id": AV}]
AV_OFF = [{"cmd": 'turn_off', "entity_id": AV}]

TV_ON = [{"cmd": 'turn_on', "entity_id": TV}]
TV_OFF = [{"cmd": 'turn_off', "entity_id": TV}]

TV2_ON = [{"cmd": 'turn_on', "entity_id": TV2_POWER}]
TV2_OFF = [{"cmd": 'turn_off', "entity_id": TV2_POWER}]
# endregion
# region Global sequences
ATV_ON = [
        {"cmd": 'turn_on', "entity_id": ATVR},
        {"cmd": 'send_command', "entity_id": ATVR, "command": "wakeup"},
        {"cmd": 'send_command', "entity_id": ATVR, "command": "top_menu"}
]
PAUSE = [{"cmd": 'media_play_pause', "entity_id": ATV}]
ATV_OFF = [{"cmd": 'send_command', "entity_id": ATVR, "command": "sleep"}]
#ATLONA_CCTV = [{"cmd": "shell_command.atlona_cctv"+('_ao' if ROOM == 'ao' else '')}]
#ATLONA_BYOD = [{"cmd": "shell_command.atlona_byod"+('_ao' if ROOM == 'ao' else '')}]
#ATLONA_ALEXPC = [{"cmd": "shell_command.atlona_alexpc"+('_ao' if ROOM == 'ao' else '')}]
#ATLONA_NVR = [{"cmd": "shell_command.atlona_nvr"+('_ao' if ROOM == 'ao' else '')}]
def Atlona(device, room = -1):
    if room == -1:
      if ROOM == 'ao': room = 1
      else: room = 0
    call = {"cmd": "mqtt.publush", "topic": f"atlona/output/{room}/set", "payload": f"{device}"}
    return [call]
    # "{"mqtt", "publish", {"topic": f"atlona/output/{room}/set", "payload": f"{device}"}
    # rethass.services.call("mqtt", "publish", {"topic": f"atlona/output/{room}/set", "payload": f"{device}"}, False)

# ATLONA_CCTV = [{"cmd": "mqtt.publish", "topic": "atlona/output/0/set", "payload": "CCTV")}]
# ATLONA_BYOD = [{"cmd": "shell_command.atlona_byod"+('_ao' if ROOM == 'ao' else '')}]
# ATLONA_ALEXPC = [{"cmd": "shell_command.atlona_alexpc"+('_ao' if ROOM == 'ao' else '')}]
# ATLONA_NVR = [{"cmd": "shell_command.atlona_nvr"+('_ao' if ROOM == 'ao' else '')}]
# endregion
# region Inputs, Outputs, Actions and Buttons
INPUTS = {
    'None': ATV_OFF+AV_OFF+TV_OFF,
    'Alex-PC': Atlona('AlexPC'),
    'NVR': Atlona('NVR'),
    'BYOD': Atlona('BYOD'),
    'CCTV': Atlona('CCTV')
}

OUTPUTS = {}
ACTIONS = {
    'TV-On': TV_ON,
    'TV-Off': TV_OFF,
    'TV2-Off': TV2_OFF,
    'TV2-On': TV2_ON,
    'Pause': PAUSE
}
BUTTONS = {
    'appletv': 'AppleTV',
    'tv': {'ON': 'TV-On', 'OF': 'TV-Off'},
    'pause': 'Pause',
    'htpc': {'ON': 'HTPC', 'OF': 'HTPC'},
    'monitor': {'ON': 'TV2-On','OF': 'TV2-Off'},
}
# endregion

# region AO internals
if ROOM == 'ao':
    TV_ATV = [{"cmd": "shell_command.ao_tv_input0"}]
    TV_AV = [{"cmd": "shell_command.ao_tv_input1"}]
    TV_HTPC = [{"cmd": "shell_command.ao_tv_input3"}]
    AV_ATLONA = [{"cmd": "media_player.select_source", "entity_id": AV, "source": 'Atlona'}]
    AV_TV = [{"cmd": "media_player.select_source", "entity_id": AV, "source": 'TV'}]
    OUT_LG_HP = [{"cmd": "webostv.select_sound_output", "entity_id": TV, "sound_output": 'external_optical'}]
    OUT_LG_AV = [{"cmd": "webostv.select_sound_output", "entity_id": TV, "sound_output": 'external_arc'}]
# endregion
# region FR internals
if ROOM == 'fr':
    AV_ATV = [{"cmd": "select_source", "entity_id": AV, "source": "AppleTV"}]
    AV_CCTV = [{"cmd": "select_source", "entity_id": AV, "source": "CCTV"}]
# endregion

# region AO actions
if ROOM == 'ao':
    OUTPUTS = {
        'None': OUT_LG_HP + [{"cmd": 'select_option', "entity_id": OUT_SELECTOR, "option": 'Headphones'}],
        'Headphones': OUT_LG_HP + [{"cmd": 'select_option', "entity_id": OUT_SELECTOR, "option": 'Headphones'}],
        'Speakers': OUT_LG_AV + [{"cmd": "select_option", "entity_id": OUT_SELECTOR, "option": 'Speakers'}],
        'Monitor-CCTV': TV2_ON + Atlona("CCTV")
    }
    INPUTS.update({
        'AppleTV': ATV_ON + TV_ON + TV_ATV,
        'HTPC': TV_ON + TV_HTPC,
        'Atlona': TV_ON + TV_AV + AV_ATLONA
    })
    ACTIONS.update({
        'AppleTV': INPUTS['AppleTV'],
        'Off': OUTPUTS['None'] + INPUTS['None'],
        'Speakers': OUTPUTS['Speakers'],
        'Headphones': OUTPUTS['None'] + AV_OFF,
        'HTPC': INPUTS['HTPC'],
        'AlexPC': INPUTS['Atlona'] + Atlona('AlexPC'),
        'Monitor-CCTV': OUTPUTS['Monitor-CCTV'],
        'Duplicate': INPUTS['Atlona']
    })
    BUTTONS['htpc'].update({'FON': 'AlexPC', 'FOF': 'Monitor-CCTV'})
    BUTTONS['tv'].update({'FON': 'Duplicate', 'FOF': 'Off'})
# endregion
# region FR actions
elif ROOM == 'fr':
    OUTPUTS.update({
        'None': 
            [
                ATV_OFF,
                {"cmd": 'select_option', "entity_id": OUT_SELECTOR, "option": 'None'}
            ],
        'Speakers': 
            [
                ATV_ON,
                {"cmd": "select_option", "entity_id": OUT_SELECTOR, "option": 'Speakers'}
            ]
    })

    INPUTS.update({
        'AppleTV': ATV_ON + TV_ON + AV_ATV,
        'Atlona': ATV_OFF + TV_ON + AV_CCTV
    })
    ACTIONS.update({
        'Off': OUTPUTS['None'] + INPUTS['None'],
        'TV-On': [{"cmd": "shell_command.fr_tv_on"}],
        'Speakers': OUTPUTS['Speakers'],
        'Alex-PC': INPUTS['Atlona'] + Atlona('AlexPC'),
        'NVR': INPUTS['Atlona'] + Atlona('NVR'),
        'BYOD': INPUTS['Atlona'] + Atlona('BYOD'),
        'CCTV': INPUTS['Atlona'] + Atlona('CCTV')
    })
    BUTTONS.update({
        'fr_tv2': {'ON': 'Monitor-On','OF': 'Monitor-Off'}
    })
# endregion

# region core functions

