#!/usr/bin/env python3
"""Initial worldepg build pipeline: fetch upstream free EPG and split feeds."""
import gzip, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent.parent
WORK=ROOT/'_upstream'
OUT=ROOT/'guide.xml'
UPSTREAM='https://github.com/iptv-org/epg.git'
DAYS=7

def run(cmd, cwd=None):
    subprocess.run(cmd, cwd=cwd, check=True)

def infer_country(channel_id, display):
    # Conservative country-code suffix heuristic. Source metadata improvements planned.
    m=re.search(r'\.([a-z]{2})$',channel_id.lower())
    if m: return m.group(1)
    m=re.search(r'\(([A-Z]{2})\)\s*$',display)
    if m: return m.group(1).lower()
    return None

def main():
    if WORK.exists(): shutil.rmtree(WORK)
    run(['git','clone','--depth','1',UPSTREAM,str(WORK)])
    # Read upstream site catalogue (SITES.md). Collect identifiers from table-like lines.
    sites_file=WORK/'SITES.md'
    sites=[]
    if sites_file.exists():
        for line in sites_file.read_text(encoding='utf-8',errors='replace').splitlines():
            if line.startswith('|') and 'http' in line.lower():
                cols=[c.strip() for c in line.strip('|').split('|')]
                for c in cols:
                    m=re.search(r'https?://([^/\s)]+)',c)
                    if m:
                        sites.append(m.group(1)); break
    sites=sorted(set(sites))
    if not sites:
        raise RuntimeError('Could not discover source identifiers in upstream SITES.md')
    # Invoke the upstream grabber in batches to stay below shell argument limits.
    produced=[]
    for i in range(0,len(sites),25):
        batch=sites[i:i+25]
        target=ROOT/f'_batch_{i//25}.xml'
        cmd=['npm','run','grab','---',f'--sites={','.join(batch)}',f'--days={DAYS}',f'--output={target}']
        run(cmd,cwd=WORK)
        if target.exists(): produced.append(target)
    if not produced: raise RuntimeError('Upstream scraper produced no batches')
    # Merge XMLTV documents, deduplicating channels and programme records.
    channels={}; programs={}
    for p in produced:
        try: tree=ET.parse(p)
        except ET.ParseError: continue
        root=tree.getroot()
        for c in root.findall('channel'):
            cid=c.get('id')
            if cid and cid not in channels: channels[cid]=c
        for prog in root.findall('programme'):
            key=(prog.get('channel'),prog.get('start'),prog.get('stop'),''.join((prog.findtext('title') or '').split()))
            programs[key]=prog
    if not channels or not programs: raise RuntimeError('Merged output empty; refusing to publish')
    merged=ET.Element('tv',{'generator-info-name':'worldepg','generator-info-url':'https://github.com/AT78/worldepg'})
    for c in channels.values(): merged.append(c)
    for p in sorted(programs.values(),key=lambda x:(x.get('start',''),x.get('channel',''))): merged.append(p)
    xml=ET.tostring(merged,encoding='utf-8',xml_declaration=True)
    OUT.write_bytes(xml); (ROOT/'guide.epg').write_bytes(xml)
    with gzip.open(ROOT/'guide.xml.gz','wb',compresslevel=9) as f: f.write(xml)
    country_channels={}; country_programs={}
    for cid,c in channels.items():
        display=c.findtext('display-name') or cid
        cc=infer_country(cid,display)
        if cc: country_channels.setdefault(cc,{})[cid]=c
    for key,p in programs.items():
        cc=infer_country(p.get('channel',''), '')
        if cc: country_programs.setdefault(cc,[]).append(p)
    countries=ROOT/'countries'; countries.mkdir(exist_ok=True)
    for cc,chs in country_channels.items():
        tv=ET.Element('tv',{'generator-info-name':'worldepg'})
        for c in chs.values(): tv.append(c)
        for p in sorted(country_programs.get(cc,[]),key=lambda x:x.get('start','')): tv.append(p)
        (countries/f'{cc}.xml').write_bytes(ET.tostring(tv,encoding='utf-8',xml_declaration=True))
    report={'generated_utc':datetime.now(timezone.utc).isoformat(),'target_days':DAYS,'source_sites_discovered':len(sites),'channels':len(channels),'programmes':len(programs),'country_feeds':len(country_channels),'coverage_note':'7-day target; actual coverage depends on free upstream sources; country attribution currently heuristic.'}
    (ROOT/'status.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    for p in produced: p.unlink(missing_ok=True)
    shutil.rmtree(WORK,ignore_errors=True)
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
