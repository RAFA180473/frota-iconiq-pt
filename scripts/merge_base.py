"""Daily merge: base fleet list (from master sheet 'OP MARGIN') + WheelSys Vehicle List + WheelSys Non Revenue Tickets.
Usage: python3 -I merge_base.py <base.json> <wheelsys.csv> <out.json> [<nrt_hist_in.json> <nrt_hist_out.json>]
wheelsys.csv: header Plate,Situacao,Localizacao,Km,NRTNo,NRTInicio,NRTFimPrevisto,NRTObs,NRTFornecedor,NotaViatura
  Situacao/Localizacao/Km/NRTNo/NRTInicio/NRTFimPrevisto/NotaViatura come from the Vehicle List Report
  (carstatus, stationname, mileage, agrno, checkoutdate, checkindate, remarks);
  NRTObs/NRTFornecedor come from the Non Revenue Tickets List (Remarks, MaintenanceSupplierName) of the open ticket.
Vehicles whose WheelSys status is 'Defleeted' (or isdefleeted=1) are excluded.
Mileage: WheelSys Km is the exact reference and always replaces the master Mileage when present.
NRT classification (rule from Nuno, 18/10/2026): only these justifications get the detailed follow-up analysis
(NRTTipo 'Acompanhamento'): Manutenção, Colisão, Avaria/Garantia (and Avaria), Venda/Devolução, Quebra de Vidros,
Pneus, Assistência em Viagem and (from 18/10/2026, Nuno) Peritagem. All other justifications (Empregado, Administração,
AVEX, Station Movement, Shuttle, Consignação/outros, ...) are internal-use static immobilisations (NRTTipo 'Estática'): they count in the
fleet immobilisation/occupancy rates but not in the NRT follow-up analysis.
Follow-up control per NRT: DiasImobilizacao (start -> now), DiasPrevistos, NRTAtrasada/DiasAtraso (expected end passed),
DiasSemAtualizacao (days since the ticket's motivo/fim previsto/observações/fornecedor/localização last changed, from
the daily snapshots kept in nrt_hist; counting starts the first day a ticket is seen) and NRTControlo (one status)."""
import sys, json, csv, re, os, unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo
NOW = datetime.now(ZoneInfo('Europe/Lisbon')).replace(tzinfo=None)
TODAY = NOW.strftime('%Y-%m-%d')
def dt(v):
    try: return datetime.fromisoformat(v[:16])
    except (TypeError, ValueError): return None
base, wcsv, out = sys.argv[1:4]
hin, hout = (sys.argv[4], sys.argv[5]) if len(sys.argv) > 5 else (None, None)
hist = json.load(open(hin, encoding='utf-8')) if hin and os.path.exists(hin) else {}
hist = hist.get('tickets', hist)
rows = json.load(open(base, encoding='utf-8'))['rows']
ws = {}
F = ('NRTNo', 'NRTInicio', 'NRTFimPrevisto', 'NRTObs', 'NRTFornecedor', 'NotaViatura')
for r in csv.DictReader(open(wcsv, encoding='utf-8')):
    km = (r.get('Km') or '').strip()
    ws[r['Plate'].strip().upper()] = (r['Situacao'].strip(), r['Localizacao'].strip(), int(km) if km.isdigit() else None,
                                      {k: ' '.join((r.get(k) or '').split()) for k in F})
loc_pt = {'Lisbon Airport': 'Lisboa Aeroporto', 'Oporto Airport': 'Porto Aeroporto', 'Faro Airport': 'Faro Aeroporto'}
def estado(s):
    if not s: return 'Sem registo WheelSys'
    if s.startswith('Rented'): return 'Alugada'
    if s.startswith('Available'): return 'Disponível'
    if s.startswith('Non Revenue'): return 'Non Revenue'
    return 'Outro'
def norm(s): return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn').strip()
GRUPOS = [('manutencao', 'Manutenção'), ('colisao', 'Colisão'), ('avaria', 'Avaria/Garantia'), ('garantia', 'Avaria/Garantia'),
          ('venda', 'Venda/Devolução'), ('devolucao', 'Venda/Devolução'), ('vidro', 'Quebra de vidros e pneus'),
          ('pneu', 'Quebra de vidros e pneus'), ('assistencia', 'Assistência em viagem'), ('peritagem', 'Peritagem')]
def grupo(m):
    n = norm(m)
    for k, g in GRUPOS:
        if k in n: return g
    return None
def num(v):
    try: return float(v)
    except (TypeError, ValueError): return 0.0
res, excl, missing, kmupd, kmanom, newhist = [], 0, 0, 0, [], {}
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
        g = grupo(r['MotivoNR'])
        ini, fim = dt(nrt.get('NRTInicio')), dt(nrt.get('NRTFimPrevisto'))
        late = bool(fim and fim < NOW)
        no = nrt.get('NRTNo', '')
        sig = '|'.join([r['MotivoNR'], nrt.get('NRTFimPrevisto', ''), nrt.get('NRTObs', ''), nrt.get('NRTFornecedor', ''), r['Localizacao']])
        h = hist.get(no) if no else None
        if h and h.get('sig') == sig: h = dict(h)
        elif h: h = dict(h, sig=sig, alterado=TODAY)
        else: h = {'sig': sig, 'visto': TODAY, 'alterado': TODAY}
        if no: newhist[no] = h
        sem_upd = max(0, (NOW - datetime.fromisoformat(h['alterado'])).days)
        r.update(NRTNo=no, NRTInicio=nrt.get('NRTInicio', ''), NRTFimPrevisto=nrt.get('NRTFimPrevisto', ''),
                 NRTObs=nrt.get('NRTObs', ''), NRTFornecedor=nrt.get('NRTFornecedor', ''), NRTNotaViatura=nrt.get('NotaViatura', ''),
                 MotivoGrupo=g or r['MotivoNR'], NRTTipo='Acompanhamento' if g else 'Estática',
                 DiasImobilizacao=max(0, (NOW - ini).days) if ini else None,
                 DiasPrevistos=max(0, (fim - ini).days) if ini and fim else None,
                 NRTAtrasada=late, DiasAtraso=(NOW - fim).days if late else 0,
                 DiasSemAtualizacao=sem_upd, NRTUltimaAlteracao=h['alterado'])
        if not g: ctl = 'Uso interno (estática)'
        elif late: ctl = 'Prazo ultrapassado'
        elif not r['NRTObs']: ctl = 'Sem observações'
        elif sem_upd > 7: ctl = 'Sem atualização há mais de 7 dias'
        else: ctl = 'Dentro do prazo'
        r['NRTControlo'] = ctl
    res.append(r)
json.dump({'rows': res}, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
if hout:
    json.dump({'tickets': newhist, 'updated': NOW.isoformat(timespec='minutes')}, open(hout, 'w', encoding='utf-8'), ensure_ascii=False)
nr = [x for x in res if x['Estado'] == 'Non Revenue']
ac = [x for x in nr if x['NRTTipo'] == 'Acompanhamento']
print(f'{len(res)} viaturas no dashboard; {excl} excluídas por defleet; {missing} sem registo no WheelSys; '
      f'{kmupd} km atualizados pelo WheelSys; km WheelSys a 0 ou abaixo do master (informativo): {kmanom or "nenhuma"}')
print(f'NRT: {len(nr)} ({len(ac)} em acompanhamento, {len(nr) - len(ac)} estáticas de uso interno); '
      f'em acompanhamento: {sum(x["NRTAtrasada"] for x in ac)} com prazo ultrapassado, {sum(not x["NRTObs"] for x in ac)} sem observações, '
      f'{sum(not x["NRTFornecedor"] for x in ac)} sem fornecedor, {sum(x["DiasSemAtualizacao"] > 7 for x in ac)} sem atualização há mais de 7 dias')
