"""Viaturas vendidas: ficheiros de vendas (Iconiq_Sales_*.xlsx / Sales_<data>.xlsx) + export de viaturas do WheelSys (Vehicles*.xlsx).
Uso: python3 -I build_vendidas.py <out.json> <ficheiros .xlsx...>
Compra/Venda c/ IVA = valor s/ IVA x 1,23. Tempo em frota = Purchase date -> Exit date do WheelSys (meses = dias / 30,4375).
Holding cost mensal (s/ IVA) = (compra s/ IVA - venda s/ IVA) / meses em frota."""
import sys, json, re
import pandas as pd
out, files = sys.argv[1], sys.argv[2:]
sales = [f for f in files if 'ales' in f.split('/')[-1]]
veh = [f for f in files if 'ehicle' in f.split('/')[-1]]
S = pd.concat([pd.read_excel(f) for f in sales], ignore_index=True)
V = pd.concat([pd.read_excel(f) for f in veh], ignore_index=True)
up = lambda s: s.fillna('').astype(str).str.strip().str.upper()
S['vin'], S['plate'] = up(S['VIN']), up(S['License Plate'])
V['vin'], V['plate'] = up(V['Vin']), up(V['Plate'])
V['pd'], V['ed'] = pd.to_datetime(V['Purchase date'], errors='coerce'), pd.to_datetime(V['Exit date'], errors='coerce')
V['days'] = (V['ed'] - V['pd']).dt.days
V = V[V['vin'] != ''].sort_values('days', ascending=False)
byvp = {(r.vin, r.plate): r for r in V.itertuples()}
byv, byp = {}, {}
for r in V.itertuples():
    byv.setdefault(r.vin, r)
    if r.plate: byp.setdefault(r.plate, r)
def cliente(s):
    s = re.sub(r'\s+', ' ', str(s) if pd.notna(s) else '').strip()
    return re.sub(r',\s*[^,]*\d{4}[^,]*$', '', s).strip(' ,')
def iso(d):
    d = pd.to_datetime(d, errors='coerce')
    return None if pd.isna(d) else d.strftime('%Y-%m-%d')
num = lambda v: None if pd.isna(v) else float(v)
rows, seen = [], set()
for d in S.to_dict('records'):
    vin, plate = d['vin'], d['plate']
    v = byvp.get((vin, plate)) or byv.get(vin) or (byp.get(plate) if plate else None)
    if not plate and v is not None: plate = v.plate
    disp = re.sub(r'\s+', ' ', str(d['Man_Mod_Variant_Display'] if pd.notna(d['Man_Mod_Variant_Display']) else '')).strip()
    make = (v.Make if v is not None and isinstance(v.Make, str) else ('Land Rover' if disp.startswith('Land Rover') else 'Mercedes-Benz' if disp.startswith('Mercedes') else disp.split(' ')[0])).strip()
    model = disp[len(make):].strip() if disp.lower().startswith(make.lower()) else disp
    cs, vs = num(d['Purchase price']), num(d['Salesprice net as in invoice'])
    meses = None
    if v is not None and pd.notna(v.days) and v.days > 0: meses = round(v.days / 30.4375, 1)
    key = plate or vin
    if key in seen: key = f'{key} ({vin[-6:]})'
    seen.add(key)
    dv = iso(d['Invoices for cars::Sales invoice date'])
    rows.append({
        'Plate': key, 'VIN': vin, 'Make': make, 'Model': model or disp,
        'Ownership': (v.Ownership if v is not None else None) or 'Sem registo na frota',
        'CarGroup': (v[8] if v is not None and isinstance(v[8], str) else None), 'Fuel': (v[38] if v is not None and isinstance(v[38], str) else None),
        'Mileage': (int(v.Mileage) if v is not None and pd.notna(v.Mileage) else None),
        'Cliente': cliente(d['Customers::Customer display']), 'Fornecedor': cliente(d['Suppliers::Name of company']),
        'Fatura': str(d['Invoices for cars::Sales invoice No displayed']).replace('.0',''),
        'DataVenda': dv, 'AnoVenda': dv[:4] if dv else 'Sem data',
        'DataEntrada': iso(v.pd) if v is not None else None, 'DataSaida': iso(v.ed) if v is not None else None,
        'CompraSemIVA': cs, 'CompraComIVA': round(cs * 1.23, 2) if cs is not None else None,
        'VendaSemIVA': vs, 'VendaComIVA': round(vs * 1.23, 2) if vs is not None else None,
        'MesesFrota': meses,
        'HoldingCost': round((cs - vs) / meses, 2) if meses and cs is not None and vs is not None else None,
    })
json.dump({'rows': rows}, open(out, 'w'), ensure_ascii=False)
m = [r for r in rows if r['MesesFrota']]
print(f"{len(rows)} viaturas vendidas; {len(m)} com tempo em frota; venda c/ IVA {sum(r['VendaComIVA'] or 0 for r in rows):,.0f}; compra c/ IVA {sum(r['CompraComIVA'] or 0 for r in rows):,.0f}; "
      f"meses médios {sum(r['MesesFrota'] for r in m)/len(m):.1f}; holding cost médio {sum(r['HoldingCost'] for r in m)/len(m):,.0f}")
