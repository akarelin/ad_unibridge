import u3
import hassapi as hass
import pprint
import inspect
#import traceback
#import sys
from collections import ChainMap, Iterable
import voluptuous as vol
from typing import Any, Callable, Dict, List, Optional


# INSTEON_SCHEMA = vol.Schema({
#   vol.Required("buttons"): dict,
#   vol.Optional("slugs"): dict,
#   vol.Required("ignore_events"): list
# })


def U(attribute: str):
  stack = inspect.stack()[1:]
  for s in stack:
    try: this = s.frame.f_locals.get('self')
    except: continue
    if this.api:
      try: value = this.api.get_app('universe').config.get(attribute)
      except: continue
      else: return value

class Universe(u3.U3Base):
  synonyms = {}
  buttons2actions = {}

  def initialize(self):
    super().initialize()
    super().load({
        vol.Required("areas"): dict,
        vol.Optional("i2_keypads"): dict,
        vol.Optional("isy_slugs"): dict,
        vol.Optional("insteon_ignore_events"): list
      })
    self.LoadKeypads()
  #  self.LoadAreas()

  @property
  def areas(self):
    return {k.lower(): v for k,v in self.config.get('areas').items()}
  @property
  def Areas(self):
    return self.config.get('areas')
  @property
  def default_namespace(self) -> str:
    return self.config.get('default_namespace')
  def _lower(self, attribute):
    try: result = {k.lower(): v for k,v in self.config.get(attribute).items()}
    except: pass
    else: return result

  def LoadKeypads(self):
    synonyms = {k: v.split('/') for k,v in self._lower('i2_keypad_synonyms').items()}
    keypads = self._lower('i2_keypads')
#    synonyms = {k.lower(): v for k,v in self.config.get('i2_keypad_synonyms').items()}
#    keypads = {k.lower(): b for (k,b) in self.config.get('i2_keypads').items()}

    for keypad,buttons in keypads.items():
      tparts = []
      for part in [p for p in keypad.split('/') if p not in ['kp']]:
        s = synonyms.get(part)
        if isinstance(s,list): tparts = [*tparts, *s]
        else: tparts.append(part)

      #tparts = [synonyms.get(part,part) for part in keypad.split('/') if part not in ['kp']]
#      keypad = '/'.join(tparts)
#      keypad = synonyms.get(keypad, keypad)
#      tparts = [part for part in keypad.split('/') if part not in ['kp']]
      area = tparts[0]
      if area in self.areas.keys():
        if len(buttons) == 8: self.buttons2actions['/'.join(tparts)] = buttons
        else: self.Warn(f"Keypad {keypad}: len({buttons}) == {len(buttons)}")
      else: self.Warn(f"Keypad {keypad}: Unknown area {area}")

      # tparts.pop('kp')
      # for t in tparts:
      #   t = t.lower()
      #   if t not in ['kp']:

      # path = [p.lower() for p in tparts if p != kp]
#    self.slugs = [s.lower() for s in self.args.get('slugs')]
#    self.areas = [a.lower() for a in self.args.get('areas')]
#    self.LoadKeypads()



    # buttonmap = {}
    # # buttonmap = self.args.get('button_map')
    # buttonmap = self.config.get('insteon').get('buttons')
    # t2a = {}
    # # Iterate through keypads
    # for t, btns in buttonmap.items():
    #   t = t.lower()
    #   if len(btns) != 8:
    #     self.Warn(f"Keypad {t}: len({btns}) == {len(btns)}")
    #     continue
    #   tparts = t.lower().split('/')
    #   if 'kp' in tparts: tparts.remove('kp')

    #   area = None
    #   keypad_areas = list(set(tparts) & set(self.areas))
    #   if keypad_areas:
    #     if len(keypad_areas) > 1:
    #       self.Error(f"Keypad {t} has multiple areas {keypad_areas}")
    #       continue
    #     else:
    #       area = keypad_areas[0]
    #   if area in tparts: tparts.remove(area)
      
    #   ktb = '/'.join(['insteon', t, 'state'])
    #   keypad_topic_sub = ktb+'/#'
    #   if keypad_topic_sub not in self.keypad_topics: self.keypad_topics.append(keypad_topic_sub)
      
    #   for i, act in enumerate(btns):
    #     if not act: continue
    #     topic = f"{ktb}/{i}"
    #     action = {"area": area, "action": act}
    #     t2a[topic] = action
    # self.map_topic2action = t2a
  # def LoadAreas(self):
  #   self.aras = U('areas')
  #   for area, body in areas.items():
  #     members = body.get('members')
  #     for m, m_body in members.items():
  #       if m_body:
  #         synonyms = m_body.get('synonyms')
  #         if synonyms:
  #           for s in synonyms: self.synonyms[s] = [area, m]

#  def get(self, property):
#    return config.get(property)
    # if attribute == 'areas': return self.areas
    # elif attribute == 'slugs': return self.slugs
    # elif attribute in ['default_namespace','namespace']: return self.default_namespace
    # elif attribute == 'insteon': return self.insteon
    # elif attribute == 'keypad_topics': return self.keypad_topics
    # elif attribute == 'map_topic2action': return self.map_topic2action
    # else: return None


#    self.default_namespace = self.args.get('default_namespace')


#    self.insteon = self.args.get('insteon')
#    self.slugs = [s.lower() for s in self.args.get('slugs')]
#    self.areas = [a.lower() for a in self.args.get('areas')]
#    self.LoadKeypads()


  # def u(self, attribute):
  #   return self.universe(attribute)
  # def universe(self, attribute):
  #   g = self.api.get_app('universe')
  #   if g and attribute: return g.get(attribute)
  #   elif g: return g
  #   else: return None
  # @property
  # def areas(self):
  #   return self.u('areas')
  # @property
  # def default_namespace(self):
  #   return self.u('default_namespace')
  # @property
  # def buttonmap(self):
  #   return self.u('buttonmap')
  # @property
  # def insteon(self):
  #   return self.u('insteon')
  # @property
  # def ignore_events(self):
  #   return self.u('insteon').get('ignore_events')

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
