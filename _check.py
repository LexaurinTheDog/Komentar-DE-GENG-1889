#!/usr/bin/env python3
"""Local evidence checks, independent HTML cross-check and manuscript diagnostics."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
import json,re,hashlib,collections,datetime
W=Path(__file__).resolve().parent
M=json.loads((W/'meta.json').read_text());O=Path(M['repo_dir'])
units=[json.loads(x) for x in (W/'units.jsonl').read_text().splitlines()]
class NormHTML(HTMLParser):
 def __init__(self):super().__init__();self.depth=0;self.active=None;self.data={}
 def handle_starttag(self,tag,attrs):
  if tag=='div':
   self.depth+=1;a=dict(attrs)
   if 'jnnorm' in a.get('class','').split():self.active=(a.get('id'),self.depth);self.data[self.active[0]]=[]
 def handle_endtag(self,tag):
  if tag=='div':
   if self.active and self.depth==self.active[1]:self.active=None
   self.depth-=1
 def handle_data(self,data):
  if self.active:self.data[self.active[0]].append(data)
def norm(s):return re.sub(r'\s+',' ',s).strip()
h=NormHTML();h.feed((W/'sources/geng-full.html').read_bytes().decode('iso-8859-1'))
html_bad=[]
for u in units:
 body=norm(' '.join(h.data.get(u['official_doknr'],[])))
 for p in u['text'].split('\n\n'):
  if norm(p) not in body:html_bad.append(u['id'])
comments={};duplicates=[];paragraphs=collections.defaultdict(list)
for f in sorted((W/'commentary').glob('*.md')):
 for m in re.finditer(r'^=== (\S+)\n(.*?)(?=^=== |\Z)',f.read_text(),re.M|re.S):
  if m[1] in comments:duplicates.append(m[1])
  comments[m[1]]=m[2].strip()
  for p in m[2].split('\n\n'):
   if len(p.strip())>=180:paragraphs[p.strip()].append(m[1])
repeated=[{'units':ids,'text':t} for t,ids in paragraphs.items() if len(set(ids))>1]
unknown=set(comments)-{u['id'] for u in units};missing={u['id'] for u in units}-set(comments)
links=[];local_count=0
for f in list(O.glob('*.md'))+list((O/'cases').glob('*.md')):
 text=f.read_text()
 for target in re.findall(r'\]\(([^\n)]+)\)',text):
  target=target.split(' "')[0].strip('<>')
  if target.startswith(('https://','http://','mailto:','#')):continue
  local_count+=1;dest=(f.parent/unquote(target.split('#')[0])).resolve()
  if not dest.exists():links.append({'from':str(f.relative_to(O)),'target':target})
checks=json.loads((W/'completeness.json').read_text())
source_hashes=[]
for p in sorted((W/'sources').rglob('*')):
 if p.is_file() and p.name!='manifest.json':source_hashes.append({'path':str(p.relative_to(W)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
(W/'sources/manifest.json').write_text(json.dumps({'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':source_hashes},ensure_ascii=False,indent=2)+'\n')
result={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'units':len(units),'commented_units':len(comments),'individual_slots':len(checks['expected_ids']),'commentary_chars':sum(map(len,comments.values())),'missing_commentary':sorted(missing),'unknown_commentary':sorted(unknown),'duplicate_commentary_ids':duplicates,'repeated_paragraphs_180plus_chars':repeated,'xml_vs_independent_official_html_mismatches':sorted(set(html_bad)),'local_links_checked':local_count,'broken_local_links':links,'completeness_ok':checks['complete'],'limitations':['Linkprüfung betrifft lokale Manuskript- und Fallkartenlinks. Externe Quellenlinks wurden durch protokollierte Abrufe geprüft, nicht jede in amtlichen Quellen enthaltene Fremdverweisung.','Wiederholungsdiagnostik erkennt identische längere Absätze; sie beweist weder Originalität sämtlicher Gedanken noch juristische Qualität.','Dies ist technische und redaktionelle Eigenkontrolle, keine unabhängige zweite Prüfung.']}
result['ok']=not(missing or unknown or duplicates or repeated or html_bad or links) and checks['complete']
(W/'technical-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
raise SystemExit(0 if result['ok'] else 1)
