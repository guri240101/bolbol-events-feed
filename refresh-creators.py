"""Public channel refresh. No private API, cookies or invented coordinates."""
import json,re,urllib.request,urllib.parse,urllib.error,datetime,time,sys,os
from pathlib import Path
CHANNEL='UCzt8rlZjpyP4i7U2U8PBRVA'
ROOT=Path(__file__).resolve().parent

def youtube_api(resource,params):
 key=os.environ.get('YOUTUBE_API_KEY','').strip()
 if not key:raise ValueError('YOUTUBE_API_KEY is not configured')
 url='https://www.googleapis.com/youtube/v3/'+resource+'?'+urllib.parse.urlencode(params)
 for attempt in range(3):
  try:
   request=urllib.request.Request(url,headers={'X-Goog-Api-Key':key,'Accept':'application/json'})
   with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)
  except urllib.error.HTTPError as e:
   if (e.code==429 or e.code>=500) and attempt<2:
    time.sleep(2**attempt);continue
   raise ValueError('YouTube API HTTP '+str(e.code)+'; check activation, restrictions and quota') from None
  except (OSError,TimeoutError):
   if attempt==2:raise ValueError('YouTube API connection failed') from None
   time.sleep(2**attempt)

def official_videos():
 channels=youtube_api('channels',{'part':'contentDetails','id':CHANNEL}).get('items',[])
 if len(channels)!=1 or channels[0].get('id')!=CHANNEL:raise ValueError('Channel identity mismatch')
 playlist=channels[0]['contentDetails']['relatedPlaylists']['uploads']
 ids=[];token='';seen=set()
 while True:
  args={'part':'contentDetails','playlistId':playlist,'maxResults':50}
  if token:args['pageToken']=token
  result=youtube_api('playlistItems',args)
  ids.extend(x['contentDetails']['videoId'] for x in result.get('items',[]))
  token=result.get('nextPageToken','')
  if not token:break
  if token in seen:raise ValueError('Repeated pagination token')
  seen.add(token)
 ids=list(dict.fromkeys(ids))
 if not ids:raise ValueError('No public uploads returned')
 details={}
 for start in range(0,len(ids),50):
  result=youtube_api('videos',{'part':'snippet,status','id':','.join(ids[start:start+50])})
  for item in result.get('items',[]):
   snippet=item.get('snippet',{})
   if snippet.get('channelId')!=CHANNEL:raise ValueError('Video channel identity mismatch')
   if item.get('status',{}).get('privacyStatus')!='public':continue
   details[item['id']]={'videoId':item['id'],'channelId':CHANNEL,'title':snippet['title'],'shortDescription':snippet.get('description',''),'publishedAt':snippet.get('publishedAt','')}
 if not details:raise ValueError('No public video descriptions returned')
 return details

def get(url):
 for attempt in range(3):
  try:
   return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read().decode('utf-8')
  except Exception:
   if attempt==2:raise
   time.sleep(2)

def embedded(text,name):
 m=re.search(r'(?:var )?'+re.escape(name)+r'\s*=\s*',text)
 if not m:raise ValueError('Public YouTube metadata unavailable')
 return json.JSONDecoder().raw_decode(text[m.end():])[0]

def channel_titles(data):
 result={}
 def walk(x):
  if isinstance(x,dict):
   r=x.get('lockupViewModel',{})
   vid=r.get('contentId','');title=r.get('metadata',{}).get('lockupMetadataViewModel',{}).get('title',{}).get('content','')
   if re.fullmatch(r'[A-Za-z0-9_-]{11}',vid) and title:result[vid]=title
   r=x.get('videoRenderer',{})
   if r.get('videoId') and r.get('title'):result[r['videoId']]=''.join(v.get('text','') for v in r['title'].get('runs',[]))
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(data);return result

def classify(title,body,regions):
 if re.search(r'일본|도쿄|오사카|후쿠오카|교토|대만|타이베이|태국|방콕|베트남|다낭|나트랑|싱가포르|홍콩|마카오|발리|미국|유럽|해외|중국|괌|사이판|필리핀|세부|하와이|몽골|호주|파리|런던',title):return None
 for r in regions:
  names=[r['label'].replace('서울 · ',''),r.get('areaName','')]
  if any(n and len(n)>1 and n in title for n in names):return r['id']
 for r in regions:
  if r.get('areaName') and re.search(r'(?:주소|📍|위치)[^\n]*'+re.escape(r['areaName']),body):return r['id']
 return None

def stops(body,known):
 lines=body.splitlines();out=[];day=1
 for i,line in enumerate(lines):
  dm=re.search(r'(\d{1,2})\s*일차',line)
  if dm:day=min(14,max(1,int(dm[1])))
  # A delimiter distinguishes itinerary times from video chapter timestamps.
  m=re.match(r'^\D*?((?:[01]?\d|2[0-3]):[0-5]\d)\s*(?:[~～–-]\s*((?:[01]?\d|2[0-3]):[0-5]\d)?\s*\||\|)\s*(.+)$',line)
  if not m and any(re.match(r'^\s*(?:📍|주소\s*[:：]|위치\s*[:：])',a) for a in lines[i+1:i+3]):
   m=re.match(r'^\D*?((?:[01]?\d|2[0-3]):[0-5]\d)\s*(?:[~～–-]\s*((?:[01]?\d|2[0-3]):[0-5]\d)?)?\s+(.+)$',line)
  if not m or int(m[1].split(':')[0])<6:continue
  name=m[3].strip()[:120];address=''
  for nextline in lines[i+1:i+5]:
   if re.search(r'\d{1,2}:\d\d',nextline):break
   a=re.match(r'^\s*(?:📍|주소\s*[:：]|위치\s*[:：])\s*(.+)',nextline)
   if a:address=a[1].strip('[] ')[:500];break
  # Reuse only an identical known name AND address; otherwise leave unmapped.
  p=next((p for p in known if p['name']==name and address and p['address']==address and p.get('lat') is not None),{})
  out.append(dict(day=day,time=m[1].zfill(5),endTime=(m[2] or '').zfill(5) if m[2] else '',name=name,address=address,lat=p.get('lat'),lng=p.get('lng'),matchedName=p.get('matchedName',''),coordinateSource=p.get('coordinateSource',''),sourceLine=line[:1000],note='',kind='transfer' if re.search(r'^(귀가|이동|취침|체크인|체크아웃)',name) else 'visit'))
 return out[:100]

def refresh():
 seed=json.loads((ROOT/'creator-seeds.json').read_text(encoding='utf-8'));target=ROOT/'creator-feed.json'
 old=json.loads(target.read_text(encoding='utf-8')) if target.exists() else {'courses':[]}
 items={c['videoUrl']:c for c in seed['courses']};items.update({c['videoUrl']:c for c in old['courses']})
 now=datetime.datetime.now(datetime.timezone.utc).isoformat();errors=[];excluded=[];pending=[]
 try:
  details={};mode='public-page'
  if os.environ.get('YOUTUBE_API_KEY','').strip():
   mode='youtube-data-api-v3';details=official_videos();ids=list(details);titles={vid:d['title'] for vid,d in details.items()}
  else:
   page=get('https://www.youtube.com/@bolbolbbu.travel/videos')
   external=re.search(r'"externalId":"([^"]+)"',page)
   if not external or external[1]!=CHANNEL:raise ValueError('Channel identity mismatch')
   ids=list(dict.fromkeys(re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"',page)))[:30]
   if not ids:raise ValueError('No public videos found')
   titles=channel_titles(embedded(page,'ytInitialData'))
  known=[s for c in seed['courses'] for s in c.get('stops',[])]
  for vid in ids:
   url='https://www.youtube.com/watch?v='+vid
   try:
    detail=details[vid] if mode=='youtube-data-api-v3' else embedded(get(url),'ytInitialPlayerResponse').get('videoDetails',{})
    if detail.get('channelId')!=CHANNEL or detail.get('videoId')!=vid:raise ValueError('Video identity unavailable')
    title=detail['title'];body=detail.get('shortDescription','');region=classify(title,body,seed['regions'])
    if not region:excluded.append(vid);continue
    existing=items.get(url)
    if existing and existing['body'].strip()==body.strip() and existing['title']==title and existing.get('stops'):continue
    parsed=stops(body,known)
    # Keep curated geocoding when the source schedule has not changed.
    if existing and existing['body'].strip()==body.strip() and existing.get('stops'):parsed=existing['stops']
    items[url]=dict(id=existing['id'] if existing else 'youtube_'+vid.lower(),region=region,title=title[:120],body=(body or title)[:20000],summary='',videoUrl=url,verified=True,checkedAt=now[:10],sourceChannelId=CHANNEL,stops=parsed,descriptionStatus='complete',scheduleStatus='parsed' if parsed else 'needs-review')
   except Exception as e:
    # Public channel cards can be read even when watch-page details are unavailable.
    # Preserve known schedules; never invent a new video's description or stops.
    title=titles.get(vid)
    if not title:
     errors.append({'videoId':vid,'error':str(e)[:150]});continue
    region=classify(title,'',seed['regions'])
    if not region:excluded.append(vid);continue
    pending.append(vid)
    if url not in items:
     items[url]=dict(id='youtube_'+vid.lower(),region=region,title=title[:120],body=title,summary='',videoUrl=url,verified=False,checkedAt=now[:10],sourceChannelId=CHANNEL,stops=[],descriptionStatus='pending')

  if len(errors)==len(ids):raise ValueError('All video detail requests failed')
  data={'kind':'bolbolplan-courses','version':1,'updatedAt':now,'channelId':CHANNEL,'source':{'ok':not errors and not pending,'mode':mode,'errors':errors,'excluded':excluded,'descriptionPending':pending},'courses':list(items.values())}
  temp=target.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');temp.replace(target)
  print(json.dumps({'courses':len(items),'checked':len(ids),'excluded':len(excluded),'errors':errors}))
  return not errors and not pending
 except Exception as e:
  print('Refresh failed; previous feed preserved:',e,file=sys.stderr);return False
if __name__=='__main__':sys.exit(0 if refresh() else 1)
