import unibridge
import json

"""
dt_consolidator:
  module: mqtt_dt
  class: dt_consolidator
  debug: true

  unifi2mqtt_pattern: 'unifi/{site}/status/wifi/{SSID}/client/{device_name}'
  unifi2dt_pattern: 'unifi2dt/{site}/{person}/{device_slug}/state'
  sites:
    creekview:
      SSIDs:
        - Creekview
    tulacosm: 
      unifi_id: iys2yyxt
      SSIDs:
        - TulaCoSM
        - TulaCo
    yakimanka:
      unifi_id: vkcj3zy8
      SSIDs:
        - Yakimanka
    svobody:
      unifi_id: i3wp5gqu

"""
class dt_consolidator(unibridge.AppMqtt):
  def initialize(self):
    self._sites = {}
    for site_name, site in self.args['sites'].items():
      site_config = {}
      ssids = []
      ssids = site.get('SSIDs')
      if ssids:
        if not isinstance(ssids, list):
          site_config['SSIDs'] = [ssids]
        elif isinstance(ssids, str):
          site_config['SSIDs'] = ssids
        self.debug("Site {} SSIDs {} {}", site_name, ssids, site_config['SSIDs'])
      site_config['unifi_id'] = site.get('unifi_id','default')
      self.debug("Site {} => {}", site_name, site_config)
      self._sites[site_name] = site_config
    self.debug("Sites {}",self._sites)
#      self._sites.append()

  #   self.parent = self.get_app(self.args["parent"])
  #   self.set_namespace(self.parent.args["mqtt_namespace"])

  #   topic = 'light/' + self.parent.args["topic"]
  #   self.parent.topic_set = topic+'/set'
  #   self.parent.topic_state = topic+'/state'

  #   self.debug("SET Topic {} | STATUS Topic {}", self.parent.topic_set, self.parent.topic_state)
  #   self.mqtt_listener = self.listen_event(self._mqtt_trigger, "MQTT_MESSAGE")
  #   # self.discover()

  # def terminate(self):
  #   try:
  #     self.cancel_listen_event(self.mqtt_listener)
  #   except:
  #     pass