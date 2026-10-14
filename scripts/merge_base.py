"""Daily merge: base fleet list (from master sheet 'dashboard a cosntruir ') + WheelSys Vehicle List.
Usage: python3 -I merge_base.py <base.json> <wheelsys.csv> <out.json>
wheelsys.csv: header Plate,Situacao,Localizacao  (WheelSys statusname / station name in English, e.g. 'Lisbon Airport').
Vehicles whose WheelSys status is 'Defleeted' (or isdefleeted=1, written as Situacao 'Defleeted') are excluded."""
import sys, json, csv, re
base, wcsv, out = sys.argv[1:4]
rows = json.load(open(base))['rows']
ws = {}
for r in csv.DictReader(open(wcsv, encoding='utf-8')):
    ws[r['Plate'].strip().upper()] = (r['Situacao'].strip(), r['Localizacao'].strip())
loc_pt = {'Lisbon Airport': 'Lisboa Aeroporto', 'Oporto Airport': 'Porto Aeroporto', 'Faro Airport': 'Faro Aeroporto'}
def estado(s):
    if not s: return 'Sem registo WheelSys'
    if s.startswith('Rented'): return 'Alugada'
    if s.startswith('Available'): return 'Disponível'
    if s.startswith('Non Revenue'): return 'Non Revenue'
    return 'Outro'
res, excl, missing = [], 0, 0
for r in rows:
    sit, loc = ws.get(r['Plate'].strip().upper(), ('', ''))
    if sit == 'Defleeted': excl += 1; continue
    if not sit: missing += 1
    m = re.match(r'Non Revenue \((.*)\)', sit)
    r = dict(r, Situacao=sit or 'Sem registo WheelSys', Localizacao=loc_pt.get(loc, loc) or 'Sem registo WheelSys',
             Estado=estado(sit), MotivoNR=m.group(1).strip() if m else '')
    res.append(r)
json.dump({'rows': res}, open(out, 'w'), ensure_ascii=False)
print(f'{len(res)} viaturas no dashboard; {excl} excluídas por defleet; {missing} sem registo no WheelSys')
