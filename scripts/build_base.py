"""Build frota_base.json (fleet to sell + sale values) from the master workbook OpMargin-Fleet ICONIQ PT.
Usage: python3 -I build_base.py <master.xlsx> <out_base.json>
Source: sheet 'OP MARGIN' (one row per vehicle in the fleet to sell; all columns of the 'dashboard' sheet plus
sale values: RESIDUAL VALUE, residual+3% (column 0.03), COM IVA, Margem, Exit date). Values are read as cached
by Excel (data_only). Localização/Situação are NOT here: they come from WheelSys (merge_base.py)."""
import sys, json, pandas as pd
master, out = sys.argv[1:3]
op = pd.read_excel(master, sheet_name='OP MARGIN')
op = op[op['Plate'].notna()].copy()
op['Plate'] = op['Plate'].astype(str).str.strip().str.upper()
op = op[op['Plate'].str.match(r'^[A-Z0-9]{2}-[A-Z0-9]{2}-[A-Z0-9]{2}$')]
def num(v):
    v = pd.to_numeric(v, errors='coerce'); return None if pd.isna(v) else round(float(v), 2)
def intn(v):
    v = pd.to_numeric(v, errors='coerce'); return None if pd.isna(v) else int(v)
def d(v, fmt='%Y-%m-%d'):
    v = pd.to_datetime(v, errors='coerce'); return v.strftime(fmt) if pd.notna(v) else None
col3 = [c for c in op.columns if str(c).strip() in ('0.03', '0,03')] or [c for c in op.columns if isinstance(c, float)]
rows = []
for _, r in op.iterrows():
    make = str(r['Make']).strip()
    rows.append({
        'Plate': r['Plate'], 'VIN': str(r['Vin']).strip(), 'Ownership': r['Ownership'], 'Category': r['Category'],
        'CarGroup': str(r['Car group']).strip(), 'Color': r['Color'], 'Model': str(r['Model']).replace('\xa0', ' ').strip(),
        'ModelYear': intn(r['Model year']), 'Seats': intn(r['Model Seats']), 'Mileage': intn(r['Mileage']),
        'FirstLicense': d(r['First license date']), 'CO2': num(r['CO2 / Kg emissions']),
        'Make': 'Mercedes-Benz' if make == 'Mercedes' else make, 'CC': intn(r['CC']), 'Fuel': r['Fuel Type'],
        'ValorComIVA': num(r['COM IVA']),
        'ExitDate': d(r['Exit date']), 'ExitMonth': d(r['Exit date'], '%Y-%m') or 'Sem data',
        'PurchasePrice': num(r['Purchase price']), 'Residual': num(r['RESIDUAL VALUE']),
        'PrecoSemIVA': num(r[col3[0]]) if col3 else None, 'Margem': num(r['Margem']),
        'LeasingCompany': (str(r['Leasing company']).strip() if pd.notna(r['Leasing company']) else None),
        'MarginPct': num(r['MARGIN %']), 'TurnoverTotal': num(r['TURNOVER TOTAL']),
    })
json.dump({'rows': rows}, open(out, 'w'), ensure_ascii=False)
print(f'{len(rows)} viaturas na base; valor de venda total {sum((x["ValorComIVA"] or 0) for x in rows):,.2f} €')
