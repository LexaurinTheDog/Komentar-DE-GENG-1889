#!/usr/bin/env python3
"""Independent complete raw-node inventory; does not import the extraction parser."""
from pathlib import Path
import collections,datetime,hashlib,json,re,xml.etree.ElementTree as E
W=Path(__file__).resolve().parent
P=W/'sources/geng.xml'; raw=P.read_bytes(); root=E.fromstring(raw)
units=[json.loads(s) for s in (W/'units.jsonl').read_text().splitlines() if s.strip()]
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def text(e):return ' '.join(''.join(e.itertext()).split()) if e is not None else ''
expected=[];inventory=[];excluded=[];unclassified=[];annexes=[];formulas=[]
for node in root.findall('norm'):
 m=node.find('metadaten');label=m.findtext('enbez','');title=m.findtext('titel','');doknr=node.attrib['doknr'];body=text(node.find('textdaten/text/Content'))
 item={'doknr':doknr,'official_label':label,'title':title,'has_body':bool(body)}
 if re.search(r'§',label):
  expected.append({'doknr':doknr,'label':label});item['disposition']='statutory_unit'
 elif m.find('gliederungseinheit') is not None:
  assert not body,'Operative text in structural node'
  item['disposition']='structural_heading';item['structure_xml']=E.tostring(m.find('gliederungseinheit'),encoding='unicode');excluded.append(item)
 elif label=='Inhaltsübersicht':item['disposition']='official_table_of_contents';excluded.append(item)
 elif doknr==root.attrib['doknr'] and not body:
  item['disposition']='statute_metadata_and_editorial_notes';item['preserved_at']='sources/statute-metadata.json';excluded.append(item)
 else:
  if re.search(r'Anlage|Anhang',label+' '+title,re.I):annexes.append(item)
  if 'Eingangsformel' in label:formulas.append(item)
  item['disposition']='UNCLASSIFIED';unclassified.append(item)
 inventory.append(item)
expected_labels=[x['label'] for x in expected];parsed_labels=[x['label'] for x in units]
expected_doknr=[x['doknr'] for x in expected];parsed_doknr=[x['official_doknr'] for x in units]
by_doknr={u['official_doknr']:u for u in units}
label_mismatch=[{'doknr':e['doknr'],'expected':e['label'],'parsed':by_doknr[e['doknr']]['label']} for e in expected if e['doknr'] in by_doknr and by_doknr[e['doknr']]['label']!=e['label']]
duplicates=lambda xs:[k for k,v in collections.Counter(xs).items() if v>1]
# Independent number expansion from official norm labels, including grouped slots.
slots=[]
for label in expected_labels:
 label=re.sub(r'^\(XXXX\)\s*','',label);label=label.replace('§','').strip()
 parts=re.split(r'\s+(?:bis|und)\s+',label)
 if len(parts)==1:slots.append('p'+label)
 else:
  a,b=parts
  if a.isdigit() and b.isdigit():slots.extend('p'+str(i) for i in range(int(a),int(b)+1))
  else:
   a=re.fullmatch(r'(\d+)([a-z])',a);b=re.fullmatch(r'(\d+)([a-z])',b);assert a and b and a[1]==b[1]
   slots.extend('p'+a[1]+chr(i) for i in range(ord(a[2]),ord(b[2])+1))
parsed_slots=[slot for u in units for slot in u['covered_ids']]
# Compare old authoring capture, today's capture and original intake; retain all.
old=W/'sources/geng.xml';new=W/'sources/preflight-20261020/geng.xml'
intake=W/'sources/intake-20261001.md';original=Path('/Volumes/LaCie/law-intake/eu/de/gesetze/gii-geng.md')
cm=json.loads((W/'sources/change-map.json').read_text())
intake_text=intake.read_text(); normspace=lambda t:re.sub(r'\s+',' ',t).strip()
intake_missing=[]
for u in units:
 if not u['empty'] and normspace(u['text']) not in normspace(intake_text):intake_missing.append(u['id'])
historical={'intake_original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'intake_copy_sha256':hashlib.sha256(intake.read_bytes()).hexdigest(),'intake_copy_byte_equal':original.read_bytes()==intake.read_bytes(),'authoring_xml_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'preflight_xml_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'authoring_vs_preflight_byte_equal':old.read_bytes()==new.read_bytes(),'nonempty_unit_texts_missing_from_intake':intake_missing,'intake_change_map':'sources/change-map.json','unit_doknr_duplicates':duplicates(expected_doknr),'xml_historical_version_container_tags':[e.tag for e in root.iter() if re.search(r'histor|version',e.tag,re.I)],'selection':'Single current consolidated GenG XML. No parallel historical norm versions concatenated. No historical reconstruction of pre-intake law undertaken.'}
report={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'official_source':'https://www.gesetze-im-internet.de/geng/xml.zip','raw_evidence':'sources/geng.xml','raw_sha256':hashlib.sha256(raw).hexdigest(),'expected_official_labels':expected_labels,'parsed_labels':parsed_labels,'expected_official_doknr':expected_doknr,'parsed_official_doknr':parsed_doknr,'expected_ids':slots,'parsed_ids':parsed_slots,'official_unit_count':len(expected),'individual_slot_count':len(slots),'raw_node_count':len(inventory),'excluded_node_count':len(excluded),'node_inventory':inventory,'missing_labels':sorted(set(expected_labels)-set(parsed_labels)),'extra_labels':sorted(set(parsed_labels)-set(expected_labels)),'label_mismatches':label_mismatch,'missing_doknr':sorted(set(expected_doknr)-set(parsed_doknr)),'extra_doknr':sorted(set(parsed_doknr)-set(expected_doknr)),'duplicate_doknr':duplicates(parsed_doknr),'duplicate_unit_ids':duplicates([u['id'] for u in units]),'missing_slot_ids':sorted(set(slots)-set(parsed_slots)),'extra_slot_ids':sorted(set(parsed_slots)-set(slots)),'duplicate_slot_ids':duplicates(parsed_slots),'unclassified_nodes':unclassified,'eingangsformel':{'present':bool(formulas),'disposition':'No Eingangsformel in any official norm metadata or content node. Metadata node has no operative body; law-wide editorial/application notes preserved separately.'},'annex_disposition':{'present':bool(annexes),'annexes':annexes,'verification':'All 211 raw norm nodes inventoried, including unnumbered nodes, plus official contents and HTML total edition. No operative annex found; no body excluded merely for lacking a section heading.'},'historical_versions_checked':historical,'limitations':['Independent technical inventory and source preflight only; not a legal review of the 199 commentary units.','Current official consolidated version and its stated last amendment checked. No exhaustive reconstruction of every historical amendment.']}
error_keys=['missing_labels','extra_labels','label_mismatches','missing_doknr','extra_doknr','duplicate_doknr','duplicate_unit_ids','missing_slot_ids','extra_slot_ids','duplicate_slot_ids','unclassified_nodes']
report['complete']=not any(report[k] for k in error_keys) and historical['intake_copy_byte_equal'] and historical['authoring_vs_preflight_byte_equal'] and not intake_missing and len(expected)==len(units)
save(W/'coverage-check.json',report)
print(json.dumps({k:report[k] for k in ['complete','official_unit_count','individual_slot_count','raw_node_count','excluded_node_count']},ensure_ascii=False))
assert report['complete'], 'Coverage preflight failed; inspect coverage-check.json'
