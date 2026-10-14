# Frota ICONIQ PT — dashboard

Dashboard da frota ativa ICONIQ PT (Auto Union), alojado no GitHub Pages.

- `index.html` — o dashboard (abre `data/frota_iconiq.json`).
- `data/frota_base.json` — lista master das viaturas (folha "dashboard a cosntruir " do ficheiro OpMargin-Fleet ICONIQ PT, SharePoint FROTA/Defleet 26).
- `data/wheelsys_latest.csv` — Localização e Situação de cada matrícula, do WheelSys (Vehicle List Report, date basis Today).
- `data/frota_iconiq.json` — base + WheelSys, sem viaturas em defleet. É o que o dashboard mostra.
- `scripts/merge_base.py` — `python3 -I scripts/merge_base.py data/frota_base.json data/wheelsys_latest.csv data/frota_iconiq.json`
- `scripts/build_frota.py` — reconstrói a partir do Excel master: `python3 -I scripts/build_frota.py master.xlsx data/wheelsys_latest.csv data/frota_iconiq.json x`

Atualização: tarefa agendada diária às 11h (Lisboa) — lê o WheelSys, corre o merge e publica aqui.

Atenção: repositório público — matrículas, VIN e valores da frota ficam visíveis na internet.
