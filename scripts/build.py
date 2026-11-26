#!/usr/bin/env python3
"""Build worldwide XMLTV feeds using the iptv-org/epg source catalogue."""
import gzip,json,re,shutil,subprocess
from pathlib import Path
from datetime import datetime,timedelta,timezone
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent.parent; WORK=ROOT/'_upstream'; DAYS=7; UPSTREAM='https://github.com/iptv-org/epg.git'
def run(cmd,cwd=None): subprocess.run(cmd,cwd=cwd,check=True)
def sites_from_catalog(path): return sorted(set(re.findall(r'href=["\']sites/([^/"\']+)["\']',path.read_text(encoding='utf-8',errors='replace'))))
def country_from_channel_id(cid):
 m=re.search(r'\.([a-z]{2})$',(cid or '').lower()); return m.group(1) if m else None
def main():
 if WORK.exists(): shutil.rmtree(WORK)
 run(['git','clone','--depth','1',UPSTREAM,str(WORK)]); run(['npm','install','--no-audit','--no-fund'],cwd=WORK)
 sites=sites_from_catalog(WORK/'SITES.md')
 if not sites: raise RuntimeError('No site IDs found in upstream SITES.md')
 batches=[]; failures=[]
 for i in range(0,len(sites),20):
  batch=sites[i:i+20]; target=ROOT/f'_batch_{i//20}.xml'
  try:
   run(['npm','run','grab','---',f'--sites={",".join(batch)}','--days=7','--maxConnections=4',f'--output={target}'],cwd=WORK)
   if target.exists() and target.stat().st_size: batches.append(target)
   else: failures.append({'sites':batch,'error':'No output file'})
  except Exception as e: failures.append({'sites':batch,'error':str(e)[:500]})
 if not batches: raise RuntimeError('All source batches failed; refusing to replace feeds')
 channels={}; programs={}
 for p in batches:
  try: root=ET.parse(p).getroot()
  except Exception as e: failures.append({'batch_file':p.name,'error':'XML parse: '+str(e)}); continue
  for c in root.findall('channel'):
   cid=c.get('id')
   if cid and cid not in channels: channels[cid]=c
  for pr in root.findall('programme'):
   key=(pr.get('channel'),pr.get('start'),pr.get('stop'),(pr.findtext('title') or '').strip()); programs[key]=pr
 if not channels or not programs: raise RuntimeError('Merged data empty; preserving existing feeds')
 now=datetime.now(timezone.utc); cutoff=now+timedelta(days=DAYS)
 def parse(v):
  try:return datetime.strptime(v[:14],'%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
  except Exception:return None
 programs={k:p for k,p in programs.items() if (parse(p.get('start','')) and parse(p.get('stop','')) and parse(p.get('stop',''))>now and parse(p.get('start',''))<cutoff)}
 used={p.get('channel') for p in programs.values()}; channels={k:v for k,v in channels.items() if k in used}
 if not channels or not programs:raise RuntimeError('No valid programme entries in seven-day window')
 def serialize(chs,progs):
  tv=ET.Element('tv',{'generator-info-name':'worldepg','generator-info-url':'https://github.com/AT78/worldepg'})
  for c in chs.values():tv.append(c)
  for p in sorted(progs,key=lambda p:(p.get('start',''),p.get('channel',''))):tv.append(p)
  return ET.tostring(tv,encoding='utf-8',xml_declaration=True)
 xml=serialize(channels,list(programs.values())); (ROOT/'guide.xml').write_bytes(xml); (ROOT/'guide.epg').write_bytes(xml)
 with gzip.open(ROOT/'guide.xml.gz','wb',compresslevel=9) as f:f.write(xml)
 ccmap={}
 for cid,c in channels.items():
  cc=country_from_channel_id(cid)
  if cc:ccmap.setdefault(cc,{})[cid]=c
 pp={}
 for p in programs.values():
  cc=country_from_channel_id(p.get('channel',''))
  if cc:pp.setdefault(cc,[]).append(p)
 countries=ROOT/'countries'; countries.mkdir(exist_ok=True)
 for old in countries.glob('*.xml'):old.unlink()
 for cc,chs in ccmap.items():(countries/f'{cc}.xml').write_bytes(serialize(chs,pp.get(cc,[])))
 report={'generated_utc':now.isoformat(),'target_days':DAYS,'source_sites_discovered':len(sites),'source_batches_attempted':(len(sites)+19)//20,'source_batches_succeeded':len(batches),'source_batch_failures':failures,'channels':len(channels),'programmes':len(programs),'country_feeds':len(ccmap),'country_method':'channel ID suffix heuristic','coverage_note':'Seven-day target; upstream coverage varies and country classification is provisional.'}
 (ROOT/'status.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 for p in batches:p.unlink(missing_ok=True)
 for p in ROOT.glob('_batch_*.xml'):p.unlink(missing_ok=True)
 shutil.rmtree(W,ignore_errors=True);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
