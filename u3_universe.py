import u3
import pprint

class Universe(u3.U3Base):
  default_namespace = None
  areas = []
  slugs = {}
  insteon = {}
  map_topic2action = {}
  keypad_topics = []
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
    elif attribute == 'keypad_topics': return self.keypad_topics
    elif attribute == 'map_topic2action': return self.map_topic2action
    else: return None

  def initialize(self):
    super().initialize()
    self.default_namespace = self.args.get('default_namespace')
    self.insteon = self.args.get('insteon')
    self.slugs = [s.lower() for s in self.args.get('slugs')]
    self.areas = [a.lower() for a in self.args.get('areas')]
    self.LoadKeypads()

  def LoadKeypads(self):
    buttonmap = {}
    buttonmap = self.args.get('button_map')
    t2a = {}
    # Iterate through keypads
    for t, btns in buttonmap.items():
      t = t.lower()
      if len(btns) != 8:
        self.Warn(f"Keypad {t}: len({btns}) == {len(btns)}")
        continue
      tparts = t.lower().split('/')
      if 'kp' in tparts: tparts.remove('kp')

      area = None
      keypad_areas = list(set(tparts) & set(self.areas))
      if keypad_areas:
        if len(keypad_areas) > 1:
          self.Error(f"Keypad {t} has multiple areas {keypad_areas}")
          continue
        else:
          area = keypad_areas[0]
      if area in tparts: tparts.remove(area)
      
      ktb = '/'.join(['insteon', t, 'state'])
      keypad_topic_sub = ktb+'/#'
      if keypad_topic_sub not in self.keypad_topics: self.keypad_topics.append(keypad_topic_sub)
      
      for i, act in enumerate(btns):
        if not act: continue
        topic = f"{ktb}/{i}"
        action = {"area": area, "action": act}
        t2a[topic] = action
    self.map_topic2action = t2a


  # def LoadKeymap(self):
  #   keymap = {}
  #   keymap = self.args.get('keymap')
  #   bm = {}
  #   for k,btns in keymap.items():
  #     if len(btns) != 8:
  #       self.Warn(f"Keypad {k}: len({btns}) == {len(btns)}")
  #       continue
  #     keypad = k.lower().split('/')
  #     base_topic = ['insteon']
  #     base_topic += keypad
  #     base_topic.append('set')
  #     if 'kp' in keypad: keypad.remove('kp')
  #     for i, indicator in enumerate(btns):
  #       if not indicator: continue
  #       topic = ['ind']
  #       keypad_areas = list(set(keypad) & set(self.areas))
  #       if len(keypad_areas) == 1: topic.append(keypad_areas[0])
  #       elif len(keypad_areas) > 1:
  #         self.Error(f"Keypad {keypad} has multiple areas {keypad_areas}")
  #         continue
  #       t1 = '/'.join(topic+[indicator.lower()])
  #       t2 = '/'.join(base_topic+[str(i)])
  #       if t1 in bm: bm[t1].append(t2)
  #       else: bm[t1] = [t2]
  #   self.Debug(pprint.pformat(bm))
  #   return bm
