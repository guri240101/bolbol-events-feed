import unittest,importlib.util
from unittest.mock import patch
from pathlib import Path
spec=importlib.util.spec_from_file_location('collector',Path(__file__).with_name('refresh-creators.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Rules(unittest.TestCase):
 def test_official_api_reads_all_pages_and_full_descriptions(self):
  calls=[]
  def api(resource,args):
   calls.append((resource,args))
   if resource=='channels':return {'items':[{'id':m.CHANNEL,'contentDetails':{'relatedPlaylists':{'uploads':'uploads'}}}]}
   if resource=='playlistItems':
    offset=50 if args.get('pageToken') else 0
    result={'items':[{'contentDetails':{'videoId':'video'+str(i)}} for i in range(offset,offset+(2 if offset else 50))]}
    if not offset:result['nextPageToken']='second'
    return result
   return {'items':[{'id':i,'snippet':{'channelId':m.CHANNEL,'title':'부산 여행','description':'11:00 | 점심\n주소: 부산 중구'},'status':{'privacyStatus':'public'}} for i in args['id'].split(',')]}
  with patch.object(m,'youtube_api',side_effect=api):result=m.official_videos()
  self.assertEqual(len(result),52)
  self.assertIn('주소:',result['video51']['shortDescription'])
  self.assertEqual(len([x for x in calls if x[0]=='videos']),2)
 def test_wrong_channel_is_rejected(self):
  with patch.object(m,'youtube_api',return_value={'items':[{'id':'wrong'}]}):
   with self.assertRaises(ValueError):m.official_videos()
 def test_schedule_without_pipe_and_chapters(self):
  result=m.stops('00:35 맛집\n🍖 11:00 점심식사: 소라편의점\n주소: 순천시 덕월길 68\n🌿 12:00~ 국가정원\n주소: 순천시 국가정원1호길 47',[])
  self.assertEqual([s['time'] for s in result],['11:00','12:00'])
 def test_domestic_and_foreign(self):
  regions=[{'id':'busan','label':'부산','areaName':'부산광역시'}]
  self.assertEqual(m.classify('부산 당일치기','',regions),'busan')
  self.assertIsNone(m.classify('부산에서 일본 도쿄로 여행','',regions))
  self.assertIsNone(m.classify('오늘 카페','',regions))
 def test_chapter_not_itinerary(self):
  self.assertEqual(m.stops('00:35 맛집\n02:03 정원',[]),[])
 def test_address_no_fake_coordinates(self):
  s=m.stops('1일차\n11:00~12:00 | 맛집\n주소: 부산광역시 중구 광복중앙로 31',[])[0]
  self.assertIsNone(s['lat']);self.assertEqual(s['time'],'11:00');self.assertIn('광복중앙로',s['address'])
 def test_public_channel_title_fallback(self):
  data={'items':[{'lockupViewModel':{'contentId':'abcdefghijk','metadata':{'lockupMetadataViewModel':{'title':{'content':'Busan trip'}}}}}]}
  self.assertEqual(m.channel_titles(data),{'abcdefghijk':'Busan trip'})
if __name__=='__main__':unittest.main()
