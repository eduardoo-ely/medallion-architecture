# Pipeline de Engenharia de Dados & Análise Estatística — Arrecadação Tributária no Brasil

**Integrantes:**
- Gabriel Fernando Simon
- Paulo Henrique Garbo
- Gustavo Henrique Telo
- Eduardo de Paula

## Arquitetura do Projeto (Medallion Architecture)
1. **Camada Bronze (`data/bronze/`):** Planilha oficial `arrecadacao-estado-tratado.xlsx` (8.613 registros mensais de Jan/2000 a Jul/2026 distribuídos nas 27 UFs e 47 colunas).
2. **Camada Silver (`data/silver/` & `src/etl_pipeline.py`):** Validação de schema (Data Quality), tratamento de nulos (`0 NaN`), preservação de retificações contábeis oficiais, mapeamento das 5 Macrorregiões e cálculo de `Total_Arrecadacao`.
3. **Camada Gold (`data/gold/analytics_gold.json` & `index.html`):** Cálculo dinâmico de medidas de posição (Aula 04/09), dispersão (Aula 11/09), tabelas de frequência/histograma e outliers pelo critério de Tukey (Aula 18/09) e correlação linear de Pearson (Aula 25/09).

## Como Executar / Hospedar no GitHub Pages
- **No GitHub Pages:** Suba todos os arquivos deste pacote na raiz do repositório e ative o GitHub Pages na branch `main`. O `index.html` carrega e calcula automaticamente o arquivo `arrecadacao-estado-tratado.xlsx` via `fetch()` (Zero Hardcode) e também permite fazer upload de qualquer nova planilha `.xlsx` ou `.csv` ao vivo!
- **Via Python Local:**
  ```bash
  pip install pandas numpy openpyxl
  python src/etl_pipeline.py
  ```
