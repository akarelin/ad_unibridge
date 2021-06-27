import u3
import pprint

class Universe(u3.U3Base):
  default_namespace = None
  areas = []
  slugs = {}
  insteon = {}
  buttonmap = {}
  ''' Example
    creekview:
      module: u3_combines
      class: Globals
      debug: True

      default_namespace: deuce
      areas: []
      keymap:
        kp/AO/AV:
          - appletv
          - htpc
          - atlona
          - 
          - sonos
          - pause
          - speakers
          - tv
        kp/BBQ:
          - 
          - 
          - 
          - 
          - 
          - 
          - 
          - 
      slugs:
        entry: entry
        stairs1: stairs/1
      insteon:
        ignore_events:
        - RR
        - OL
        - ST
    '''

  def get(self, attribute):
    if attribute == 'areas': return self.areas
    elif attribute == 'slugs': return self.slugs
    elif attribute in ['default_namespace','namespace']: return self.default_namespace
    elif attribute == 'insteon': return self.insteon
    elif attribute == 'buttonmap': return self.buttonmap
    else: return None

  def initialize(self):
    super().initialize()
    self.default_namespace = self.args.get('default_namespace')
    self.insteon = self.args.get('insteon')
    self.slugs = [s.lower() for s in self.args.get('slugs')]
    self.areas = [a.lower() for a in self.args.get('areas')]
    self.buttonmap = self.LoadKeymap()

  def LoadKeymap(self):
    keymap = {}
    keymap = self.args.get('keymap')
    bm = {}
    for k,btns in keymap.items():
      if len(btns) != 8:
        self.Warn(f"Keypad {k}: len({btns}) == {len(btns)}")
        continue
      keypad = k.lower().split('/')
      base_topic = ['insteon']
      base_topic += keypad
      base_topic.append('set')
      if 'kp' in keypad: keypad.remove('kp')
      for i, indicator in enumerate(btns):
        if not indicator: continue
        topic = ['ind']
        keypad_areas = list(set(keypad) & set(self.areas))
        if len(keypad_areas) == 1: topic.append(keypad_areas[0])
        elif len(keypad_areas) > 1:
          self.Error(f"Keypad {keypad} has multiple areas {keypad_areas}")
          continue
        t1 = '/'.join(topic+[indicator.lower()])
        t2 = '/'.join(base_topic+[str(i)])
        if t1 in bm: bm[t1].append(t2)
        else: bm[t1] = [t2]
    self.Debug(pprint.pformat(bm))
    return bm
