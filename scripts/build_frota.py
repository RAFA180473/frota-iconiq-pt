"""Merge master sheet 'dashboard a cosntruir ' with WheelSys Vehicle List (Localização/Situação).
Usage: python3 build_frota.py <master.xlsx> <wheelsys.csv> <out.json> <iso_ts>
wheelsys.csv columns: Plate,Situacao,Localizacao  (Situacao 'Defleeted' rows are excluded)"""
import sys, json, re, pandas as pd
master, wcsv, out, ts = sys.argv[1:5]
m = pd.read_excel(master, sheet_name='dashboard a cosntruir ')
m = m[m['Plate'].notna()].copy()
m.columns = [c.strip() for c in m.columns]
w = pd.read_csv(wcsv)
w['Plate'] = w['Plate'].str.strip().str.upper()
m['Plate'] = m['Plate'].astype(str).str.strip().str.upper()
m = m.drop(columns=[c for c in ['Localização','Situação'] if c in m.columns]).merge(w, on='Plate', how='left')
m = m[m['Situacao'].fillna('') != 'Defleeted']
def estado(s):
    if not isinstance(s,str): return 'Sem registo WheelSys'
    if s.startswith('Rented'): return 'Alugada'
    if s.startswith('Available'): return 'Disponível'
    if s.startswith('Non Revenue'): return 'Non Revenue'
    return 'Outro'
def motivo(s):
    r = re.match(r'Non Revenue \((.*)\)', s or '')
    return r.group(1).strip() if r else ''
loc_pt = {'Lisbon Airport':'Lisboa Aeroporto','Oporto Airport':'Porto Aeroporto','Faro Airport':'Faro Aeroporto'}
rows=[]
for _,r in m.iterrows():
    sit = r['Situacao'] if isinstance(r['Situacao'],str) else ''
    fld = r['First license date']
    rows.append({
        'Plate': r['Plate'], 'VIN': str(r['Vin']).strip(), 'Ownership': r['Ownership'], 'Category': r['Category'],
        'CarGroup': str(r['Car group']).strip(), 'Color': r['Color'], 'Model': str(r['Model']).replace('\xa0',' ').strip(),
        'ModelYear': int(r['Model year']) if pd.notna(r['Model year']) else None, 'Seats': int(r['Model Seats']) if pd.notna(r['Model Seats']) else None,
        'Mileage': int(r['Mileage']) if pd.notna(r['Mileage']) else None,
        'FirstLicense': fld.strftime('%Y-%m-%d') if (hasattr(fld,'strftime') and pd.notna(fld)) else None,
        'CO2': r['CO2 / Kg emissions'] if pd.notna(r['CO2 / Kg emissions']) else None,
        'Make': 'Mercedes-Benz' if str(r['Make']).strip()=='Mercedes' else str(r['Make']).strip(),
        'CC': int(r['CC']) if pd.notna(r['CC']) else None, 'Fuel': r['Fuel Type'],
        'ValorComIVA': float(r['COM IVA']) if pd.notna(r['COM IVA']) else None,
        'Localizacao': loc_pt.get(r['Localizacao'], r['Localizacao']) if isinstance(r['Localizacao'],str) else 'Sem registo WheelSys',
        'Situacao': sit or 'Sem registo WheelSys', 'Estado': estado(sit or None), 'MotivoNR': motivo(sit),
    })
json.dump({'rows':rows}, open(out,'w'), ensure_ascii=False)
print(len(rows), 'rows; excluded defleet:', int((w['Situacao']=='Defleeted').sum()))
