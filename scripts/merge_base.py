"""Daily merge: base fleet list (from master sheet 'dashboard a cosntruir ') + WheelSys Vehicle List.
Usage: python3 -I merge_base.py <base.json> <wheelsys.csv> <out.json>
wheelsys.csv: header Plate,Situacao,Localizacao[,Km,NRTNo,NRTInicio,NRTFimPrevisto,NRTObs]  (WheelSys statusname / station name in English, e.g. 'Lisbon Airport';
Km = WheelSys 'mileage' field, current odometer; NRT* = for Non Revenue vehicles, the WheelSys agreement
(agrno), its start (checkoutdate), expected end (checkindate) and remarks).
For Non Revenue vehicles DiasImobilizacao = whole days from NRTInicio to the run time (Europe/Lisbon),
DiasPrevistos = days from NRTInicio to NRTFimPrevisto, NRTAtrasada = expected end already past.
Vehicles whose WheelSys status is 'Defleeted' (or isdefleeted=1, written as Situacao 'Defleeted') are excluded.
Mileage: WheelSys Km is the exact reference and always replaces the master-file Mileage when present
(the master value is kept only for vehicles without a WheelSys Km). Big differences vs master are only reported."""
import sys, json, csv, re
from datetime import datetime
from zoneinfo import ZoneInfo
NOW = datetime.now(ZoneInfo('Europe/Lisbon')).replace(tzinfo=None)
def dt(v):
    try: return datetime.fromisoformat(v[:16])
    except (TypeError, ValueError): return None
base, wcsv, out = sys.argv[1:4]
rows = json.load(open(base))['rows']
ws = {}
for r in csv.DictReader(open(wcsv, encoding='utf-8')):
    km = (r.get('Km') or '').strip()
    ws[r['Plate'].strip().upper()] = (r['Situacao'].strip(), r['Localizacao'].strip(), int(km) if km.isdigit() else None,
                                      {k: (r.get(k) or '').strip() for k in ('NRTNo', 'NRTInicio', 'NRTFimPrevisto', 'NRTObs')})
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
    sit, loc, km, nrt = ws.get(r['Plate'].strip().upper(), ('', '', None, {}))
    if sit == 'Defleeted': excl += 1; continue
    if not sit: missing += 1
    m = re.match(r'Non Revenue \((.*)\)', sit)
    r = dict(r, Situacao=sit or 'Sem registo WheelSys', Localizacao=loc_pt.get(loc, loc) or 'Sem registo WheelSys',
             Estado=estado(sit), MotivoNR=m.group(1).strip() if m else '')
    if km is not None:
        mm = num(r.get('Mileage'))
        if km == 0 or km < mm:
            kmanom.append(f"{r['Plate']} (WheelSys {km}, master {r.get('Mileage')})")
        r['Mileage'] = km; r['MileageFonte'] = 'WheelSys'; kmupd += 1
    else:
        r['MileageFonte'] = 'Ficheiro master'
    if r['Estado'] == 'Non Revenue':
        ini, fim = dt(nrt.get('NRTInicio')), dt(nrt.get('NRTFimPrevisto'))
        r.update(NRTNo=nrt.get('NRTNo', ''), NRTInicio=nrt.get('NRTInicio', ''), NRTFimPrevisto=nrt.get('NRTFimPrevisto', ''),
                 NRTObs=nrt.get('NRTObs', ''),
                 DiasImobilizacao=max(0, (NOW - ini).days) if ini else None,
                 DiasPrevistos=max(0, (fim - ini).days) if ini and fim else None,
                 NRTAtrasada=bool(fim and fim < NOW))
    res.append(r)
json.dump({'rows': res}, open(out, 'w'), ensure_ascii=False)
print(f'{len(res)} viaturas no dashboard; {excl} excluídas por defleet; {missing} sem registo no WheelSys; '
      f'{kmupd} km atualizados pelo WheelSys; km WheelSys a 0 ou abaixo do master (informativo): {kmanom or "nenhuma"}')
