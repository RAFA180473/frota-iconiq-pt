"""Build manutencoes.json (maintenance due / within 2,500 km) from the WheelSys Service Planner.
Usage: python3 -I build_manut.py <service_planner.txt> <frota_iconiq.json> <out.json>
service_planner.txt (decoded text from the browser, Service planner with "Active vehicles"):
  line 1: number of active vehicles in the planner
  line 2: model names separated by '~'
  line 3: rows separated by ',' -> plate(no hyphens)|odometer|last maint km (1_lkm)|next maint km (1_nkm)|
          last date (1_ldt yyyymmdd)|next inspection date (4_ndt yyyymmdd)|model index|station L/P/F|check-in yyyymmddHHMM
  Only vehicles with next maintenance km - odometer <= 2500 are sent (overdue included).
Each row is joined with the dashboard fleet (frota_iconiq.json) by plate for make/model/contract/situation."""
import sys, json
from datetime import datetime
from zoneinfo import ZoneInfo
NOW = datetime.now(ZoneInfo('Europe/Lisbon')).replace(tzinfo=None)
src, frota, out = sys.argv[1:4]
lines = open(src, encoding='utf-8').read().split('\n')
total = int(lines[0]); models = lines[1].split('~'); rows_txt = [x for x in lines[2].split(',') if x]
F = {r['Plate']: r for r in json.load(open(frota, encoding='utf-8'))['rows']}
ST = {'L': 'Lisboa Aeroporto', 'P': 'Porto Aeroporto', 'F': 'Faro Aeroporto'}
d8 = lambda s: f'{s[:4]}-{s[4:6]}-{s[6:8]}' if len(s) >= 8 else ''
res = []
for t in rows_txt:
    p, odo, lkm, nkm, ldt, ipo, mi, st, ci = t.split('|')
    plate = f'{p[:2]}-{p[2:4]}-{p[4:]}'
    odo, lkm, nkm = int(odo), int(lkm), int(nkm)
    rem = nkm - odo
    f = F.get(plate, {})
    checkin = f'{d8(ci)}T{ci[8:10]}:{ci[10:12]}' if len(ci) >= 12 else ''
    res.append({
        'Plate': plate, 'Km': odo, 'UltimaManutKm': lkm or None, 'ProximaManutKm': nkm, 'KmRestantes': rem,
        'KmAtraso': -rem if rem < 0 else 0,
        'EstadoManut': 'Vencida' if rem <= 0 else 'Faltam até 2 500 km',
        'RegistoManut': 'Com registo' if lkm else 'Sem manutenção registada',
        'DataReferencia': d8(ldt), 'ProximaInspecao': d8(ipo),
        'Localizacao': ST.get(st, st), 'CheckInPrevisto': checkin,
        'Make': f.get('Make', ''), 'Model': f.get('Model') or (models[int(mi)] if mi.isdigit() and int(mi) < len(models) else ''),
        'CarGroup': f.get('CarGroup', ''), 'Ownership': f.get('Ownership', ''),
        'Estado': f.get('Estado', 'Fora da base'), 'Situacao': f.get('Situacao', ''), 'MotivoNR': f.get('MotivoNR', ''),
        'NaBase': bool(f), 'AtivasPlanner': total,
    })
res.sort(key=lambda r: r['KmRestantes'])
json.dump({'rows': res, 'updated': NOW.isoformat(timespec='minutes')}, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
v = [r for r in res if r['EstadoManut'] == 'Vencida']
print(f'{len(res)} viaturas com manutenção vencida ou a menos de 2 500 km ({len(v)} vencidas, {len(res) - len(v)} a menos de 2 500 km) '
      f'de {total} ativas no Service Planner; {sum(not r["UltimaManutKm"] for r in res)} sem manutenção registada; '
      f'{sum(not r["NaBase"] for r in res)} fora da base do dashboard.')
