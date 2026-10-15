"""Daily merge: base fleet list (from master sheet 'dashboard a cosntruir ') + WheelSys Vehicle List.
Usage: python3 -I merge_base.py <base.json> <wheelsys.csv> <out.json>
wheelsys.csv: header Plate,Situacao,Localizacao[,Km]  (WheelSys statusname / station name in English, e.g. 'Lisbon Airport';
Km = WheelSys 'mileage' field, current odometer).
Vehicles whose WheelSys status is 'Defleeted' (or isdefleeted=1, written as Situacao 'Defleeted') are excluded.
Mileage: WheelSys Km replaces the master-file Mileage when Km > 0 and Km >= master Mileage (odometer never goes back);
otherwise the master value is kept and the plate is reported as a km anomaly."""
import sys, json, csv, re
base, wcsv, out = sys.argv[1:4]
rows = json.load(open(base))['rows']
ws = {}
for r in csv.DictReader(open(wcsv, encoding='utf-8')):
    km = (r.get('Km') or '').strip()
    ws[r['Plate'].strip().upper()] = (r['Situacao'].strip(), r['Localizacao'].strip(), int(km) if km.isdigit() else None)
loc_pt = {'Lisbon Airport': 'Lisboa Aeroporto', 'Oporto Airport': 'Porto Aeroporto', 'Faro Airport': 'Faro Aeroporto'}
def estado(s):
    if not s: return 'Sem registo WheelSys'
    if s.startswith('Rented'): return 'Alugada'
    if s.startswith('Available'): return 'Disponível'
    if s.startswith('Non Revenue'): return 'Non Revenue'
    return 'Outro'
def num(v):
    try: return float(v)
    except (TypeError, ValueError): return 0.0
res, excl, missing, kmupd, kmanom = [], 0, 0, 0, []
for r in rows:
    sit, loc, km = ws.get(r['Plate'].strip().upper(), ('', '', None))
    if sit == 'Defleeted': excl += 1; continue
    if not sit: missing += 1
    m = re.match(r'Non Revenue \((.*)\)', sit)
    r = dict(r, Situacao=sit or 'Sem registo WheelSys', Localizacao=loc_pt.get(loc, loc) or 'Sem registo WheelSys',
             Estado=estado(sit), MotivoNR=m.group(1).strip() if m else '')
    if km is not None:
        if km > 0 and km >= num(r.get('Mileage')):
            r['Mileage'] = km; r['MileageFonte'] = 'WheelSys'; kmupd += 1
        else:
            r['MileageFonte'] = 'Ficheiro master'; kmanom.append(f"{r['Plate']} (WheelSys {km}, master {r.get('Mileage')})")
    res.append(r)
json.dump({'rows': res}, open(out, 'w'), ensure_ascii=False)
print(f'{len(res)} viaturas no dashboard; {excl} excluídas por defleet; {missing} sem registo no WheelSys; '
      f'{kmupd} km atualizados pelo WheelSys; anomalias de km: {kmanom or "nenhuma"}')
