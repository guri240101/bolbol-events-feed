const plain=s=>String(s||'').replace(/<[^>]*>/g,' ').replace(/&nbsp;|&#160;/g,' ').replace(/\s+/g,' ').trim();
export function registrationFacts(event,html){
 const text=plain(html),patch={};let offerStart=event.registrationDate;for(const m of html.matchAll(/<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/g)){try{const p=[JSON.parse(m[1])].flat().find(p=>p['@type']==='SportsEvent');if(p)offerStart=(Array.isArray(p.offers)?p.offers[0]:p.offers)?.validFrom;}catch{}}
 // Read only structured offer expiry. Never infer deadlines from arbitrary dates (refunds, race dates).
 for(const m of html.matchAll(/<script[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/g)){
  try{const docs=[JSON.parse(m[1])].flat();const sports=docs.find(p=>p['@type']==='SportsEvent');
  const faq=docs.find(p=>p['@type']==='FAQPage');
  for(const q of faq?.mainEntity||[]){
   if(!/접수.*언제까지/.test(q.name||''))continue;
   const a=plain(q.acceptedAnswer?.text),m=a.match(/^(\d{1,2})월\s*(\d{1,2})일부터\s*(\d{1,2})월\s*(\d{1,2})일까지 접수/);
   const start=offerStart;if(m&&/^20\d\d-\d\d-\d\d$/.test(start||'')&&Number(start.slice(5,7))===Number(m[1])&&Number(start.slice(8))===Number(m[2])){
    const year=Number(start.slice(0,4))+(Number(m[3])<Number(m[1])?1:0);patch.registrationEndDate=year+'-'+m[3].padStart(2,'0')+'-'+m[4].padStart(2,'0');patch.registrationSourceUrl=event.sourceUrl;patch.registrationEvidence='수집 사이트의 접수 FAQ · 조기 마감은 신청 사이트 확인';
   }
  }
const offer=Array.isArray(sports?.offers)?sports.offers[0]:sports?.offers;const end=offer?.validThrough||offer?.availabilityEnds;if(/^20\d\d-\d\d-\d\d/.test(end||'')){patch.registrationEndDate=end.slice(0,10);if(/T\d\d:\d\d/.test(end)&&/([+-]\d\d:\d\d|Z)$/.test(end))patch.registrationEndAt=end;}}catch{}
 }
 if(event.id==='marathon_gyeongbuk-docheong-2026'&&/2026년\s*11월\s*8일/.test(text)){
  const m=text.match(/신\s*청\s*기\s*간\s*2026년\s*(\d+)월\s*(\d+)일[\s\S]{0,60}?~\s*2026년\s*(\d+)월\s*(\d+)일[^\d]{0,12}(\d+)시까지/);
  if(m){const date=(month,day)=>'2026-'+month.padStart(2,'0')+'-'+day.padStart(2,'0');patch.registrationDate=date(m[1],m[2]);patch.registrationEndDate=date(m[3],m[4]);patch.registrationEndAt=patch.registrationEndDate+'T'+m[5].padStart(2,'0')+':00:00+09:00';patch.registrationSourceUrl='https://1004.tbc.co.kr/sub1_1.php';patch.description='경북도청 천년숲 앞 · 하프·10km·5km. 공식 요강의 신청 마감 시각을 반영합니다. 선착순으로 조기 마감될 수 있습니다.';}
 }
 return patch;
}
export async function enrichRegistration(events,get,now=new Date().toISOString()){
 const result=[];for(const event of events){if(event.kind!=='marathon'){result.push(event);continue;}let e={...event};if(e.id==='marathon_gyeongbuk-docheong-2026'){try{const patch=registrationFacts(e,await get('https://1004.tbc.co.kr/sub1_1.php'));if(!patch.registrationEndAt)throw Error('공식 접수기간 형식 변경');e={...e,...patch,registrationCheckedAt:now,registrationCheckError:null};}catch(error){e.registrationCheckError=error.message;}}result.push(e);}return result;
}
