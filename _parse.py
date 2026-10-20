#!/usr/bin/env python3
"""Reproducible extraction of the preserved GII XML, including official empty ranges."""
import xml.etree.ElementTree as E
import pathlib,json,re,hashlib,collections
W=pathlib.Path(__file__).resolve().parent
RAW=W/'sources/geng.xml'
def flat(e):
    if e is None:return ''
    out=e.text or ''
    for c in e:
        if c.tag=='BR':out+='\n'
        elif c.tag in ('DL','DT','DD','P','row','entry','LA'):
            out+='\n'+flat(c)+'\n'
        else:out+=flat(c)
        out+=c.tail or ''
    return out

def render(e):
    return '\n'.join(re.sub(r'[ \t\r\f\v]+',' ',s).strip() for s in flat(e).splitlines() if s.strip())
def paragraphs(e):
    if e is None:return ''
    return '\n\n'.join(render(c) for c in e if render(c))
def ids(label):
    t=label.replace('(XXXX) ','').replace('§','').strip()
    if ' bis ' in t or ' und ' in t:
        a,b=re.split(r' bis | und ',t)
        if a.isdigit(): return ['p'+str(x) for x in range(int(a),int(b)+1)]
        am=re.fullmatch(r'(\d+)([a-z])',a);bm=re.fullmatch(r'(\d+)([a-z])',b)
        assert am and bm and am[1]==bm[1]
        return ['p'+am[1]+chr(x) for x in range(ord(am[2]),ord(bm[2])+1)]
    return ['p'+t]
r=E.parse(RAW).getroot();units=[];structure=[];section=0; chapters={}; canonical=[];dispositions=[]
for n in r.findall('norm'):
    m=n.find('metadaten');g=m.find('gliederungseinheit');label=m.findtext('enbez','')
    if g is not None:
        section=int(re.search(r'\d+',g.findtext('gliederungsbez'))[0]); title=' '.join(g.findtext('gliederungstitel').split());structure=[f'Abschnitt {section} — {title}']; chapters[section]=title;continue
    if '§' not in label:continue
    # Preserve the official label verbatim; only stable machine IDs omit (XXXX).
    uidlist=ids(label);uid=uidlist[0] if len(uidlist)==1 else uidlist[0]+'-'+uidlist[-1][1:]
    title=' '.join(m.findtext('titel','').split());content=n.find('textdaten/text/Content');text=paragraphs(content)
    empty='weggefallen' in title and not text.strip()
    if empty:text=title
    notes=[];fn=n.find('textdaten/fussnoten/Content')
    if fn is not None and render(fn):notes.append(render(fn))
    # split the long governance and audit sections without changing legal hierarchy
    num=int(re.search(r'\d+',label)[0]);chapter=section
    if section==3:chapter=3 if num<=42 else 4
    elif section>=4:chapter=section+1
    u={'id':uid,'label':label,'title':title,'chapter':chapter,'structure':structure[:],'text':text,'notes':notes,'official_doknr':n.attrib['doknr'],'covered_ids':uidlist,'empty':bool('weggefallen' in title)}
    units.append(u);canonical += ['### '+label+' '+title,text]+notes
    if u['empty']:dispositions.append({'official_label':label,'ids':uidlist,'disposition':'Amtlicher Wegfallvermerk; kein historischer Normtext eingefügt.'})
meta={'cc':'de','lang':'de','repo':'Komentar-DE-GENG-1889','repo_dir':'/Volumes/LaCie/open-commentary/de/Komentar-DE-GENG-1889','title':'Kommentar zum Genossenschaftsgesetz (GenG)','source_path':str(W/'sources/canonical.txt'),'intro_file':'00-einleitung.md','intro_desc':'Stand, Methode und Benutzung','labels':{'text':'Wortlaut der Vorschrift','chapter':'Kommentarkapitel','notes':'Amtlicher Hinweis'},'chapters':[],'authoring_date':'2026-10-19','source_url':'https://www.gesetze-im-internet.de/geng/'}
for c in sorted(set(u['chapter'] for u in units)):
    sec=c if c<4 else (3 if c==4 else c-1)
    title=chapters[sec]
    if c==3:title+=' — Vorstand und Aufsichtsrat'
    if c==4:title+=' — Willensbildung und Beschlüsse'
    meta['chapters'].append({'n':c,'slug':f'abschnitt-{sec}'+('-organe' if c==3 else '-beschluesse' if c==4 else ''),'title':title})
(W/'meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
(W/'units.jsonl').write_text(''.join(json.dumps(u,ensure_ascii=False)+'\n' for u in units))
(W/'sources/canonical.txt').write_text('\n\n'.join(canonical)+'\n')
# Preserve the law-wide editorial/application notes without presenting them as a
# separate operative provision. There is no Eingangsformel node in this XML.
head=r.findall('norm')[0]
statute_metadata={'official_doknr':head.attrib['doknr'],
    'metadaten_xml':E.tostring(head.find('metadaten'),encoding='unicode'),
    'notes':paragraphs(head.find('textdaten/fussnoten/Content'))}
(W/'sources/statute-metadata.json').write_text(json.dumps(statute_metadata,ensure_ascii=False,indent=2)+'\n')
# Independently enumerate the official contents table, not the extracted units.
toc=next(n for n in r.findall('norm') if n.findtext('metadaten/enbez')=='Inhaltsübersicht')
expected_labels=[]
for row in toc.findall('.//row'):
    entries=row.findall('entry')
    if entries:
        x=render(entries[0])
        if x.startswith('§'):expected_labels.append(x)
expected=[i for x in expected_labels for i in ids(x)]
parsed=[i for u in units for i in u['covered_ids']]
report={'source_url':meta['source_url'],'raw_xml':'sources/geng.xml','raw_sha256':hashlib.sha256(RAW.read_bytes()).hexdigest(),'expected_official_labels':expected_labels,'expected_ids':expected,'parsed_ids':parsed,'official_unit_count':len(expected_labels),'commentary_unit_count':len(units),'individual_slot_count':len(expected),'missing_ids':sorted(set(expected)-set(parsed)),'unexpected_ids':sorted(set(parsed)-set(expected)),'duplicate_ids':[x for x,c in collections.Counter(parsed).items() if c>1],'empty_slot_disposition':dispositions,'annex_disposition':'Keine Anlagen im amtlichen XML oder in dessen Inhaltsübersicht; alle Normknoten einschließlich Schluss- und Übergangsvorschriften bis § 177 ausgewertet. Inhaltsübersicht und zehn Abschnittsüberschriften sind Struktur, keine zusätzlichen gesetzlichen Regelungen.','grouping':'Sechs amtlich zusammengefasste weggefallene Bereiche bleiben jeweils eine Kommentierungseinheit; sämtliche Einzelnummern werden in covered_ids nachgewiesen.'}
assert not report['missing_ids'] and not report['unexpected_ids'] and not report['duplicate_ids']
report['complete']=True
(W/'completeness.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print({k:report[k] for k in ['official_unit_count','commentary_unit_count','individual_slot_count','complete']})
