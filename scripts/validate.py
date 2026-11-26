#!/usr/bin/env python3
"""Validate generated XMLTV outputs before publication."""
import gzip,json
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent.parent
def parse(path):
 root=ET.parse(path).getroot()
 if root.tag!='tv':raise ValueError(f'{path}: root element must be tv')
 channels={c.get('id') for c in root.findall('channel') if c.get('id')}
 programmes=root.findall('programme')
 if programmes and not channels:raise ValueError(f'{path}: programmes without channels')
 for p in programmes:
  if p.get('channel') not in channels:raise ValueError(f'{path}: programme references missing channel')
 return len(channels),len(programmes)
def main():
 for name in ('guide.xml','guide.epg'):
  p=ROOT/name
  if not p.exists():raise FileNotFoundError(p)
  c,n=parse(p);print(f'{name}: {c} channels, {n} programmes')
 with gzip.open(ROOT/'guide.xml.gz','rb') as f:ET.fromstring(f.read())
 report=json.loads((ROOT/'status.json').read_text())
 if report.get('target_days')!=7:raise ValueError('status target_days should be 7')
 countries=ROOT/'countries'
 for p in countries.glob('*.xml'):
  parse(p)
 print(f'Validated {len(list(countries.glob("*.xml")))} country files and compressed guide')
if __name__=='__main__':main()
