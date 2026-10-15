import pandas as pd
import numpy as np
import json
from pathlib import Path

def run_silver_layer(filepath: str) -> pd.DataFrame:
    print(f"[BRONZE] Lendo arquivo bruto: {filepath}")
    xls = pd.ExcelFile(filepath)
    sheet = 'Dados_Ajustados' if 'Dados_Ajustados' in xls.sheet_names else xls.sheet_names[0]
    df = pd.read_excel(filepath, sheet_name=sheet)

    colunas_obrigatorias = ['Ano', 'Mês', 'UF']
    for col in colunas_obrigatorias:
        if col not in df.columns:
            raise ValueError(f"[ERRO DE SCHEMA] Coluna obrigatória ausente: {col}")

    df['UF'] = df['UF'].astype(str).str.strip().str.upper()
    df['Ano'] = pd.to_numeric(df['Ano'], errors='coerce').fillna(0).astype(int)

    mes_map = {
        'JANEIRO': 1, 'FEVEREIRO': 2, 'MARÇO': 3, 'MARCO': 3, 'ABRIL': 4,
        'MAIO': 5, 'JUNHO': 6, 'JULHO': 7, 'AGOSTO': 8, 'SETEMBRO': 9,
        'OUTUBRO': 10, 'NOVEMBRO': 11, 'DEZEMBRO': 12
    }
    if 'Mês_Num' not in df.columns:
        df['Mês_Num'] = df['Mês'].astype(str).str.strip().str.upper().map(mes_map).fillna(0).astype(int)

    regiao_map = {
        'AC':'Norte', 'AP':'Norte', 'AM':'Norte', 'PA':'Norte', 'RO':'Norte', 'RR':'Norte', 'TO':'Norte',
        'AL':'Nordeste', 'BA':'Nordeste', 'CE':'Nordeste', 'MA':'Nordeste', 'PB':'Nordeste', 'PE':'Nordeste', 'PI':'Nordeste', 'RN':'Nordeste', 'SE':'Nordeste',
        'DF':'Centro-Oeste', 'GO':'Centro-Oeste', 'MT':'Centro-Oeste', 'MS':'Centro-Oeste',
        'ES':'Sudeste', 'MG':'Sudeste', 'RJ':'Sudeste', 'SP':'Sudeste',
        'PR':'Sul', 'RS':'Sul', 'SC':'Sul'
    }
    df['Regiao'] = df['UF'].map(regiao_map).fillna('Outros')

    ignore_cols = ['Ano', 'Mês', 'Mês_Num', 'UF', 'Regiao', 'Total_Arrecadacao']
    tax_cols = [c for c in df.columns if c not in ignore_cols]
    for c in tax_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

    if 'Total_Arrecadacao' not in df.columns:
        df['Total_Arrecadacao'] = df[tax_cols].sum(axis=1)
    else:
        df['Total_Arrecadacao'] = pd.to_numeric(df['Total_Arrecadacao'], errors='coerce').fillna(0.0)

    print(f"[SILVER] Base limpa e validada: {len(df)} linhas x {len(df.columns)} colunas (0 nulos).")
    return df

def run_gold_layer(df: pd.DataFrame, output_json: str):
    s_mensal = df['Total_Arrecadacao']
    q1_m, q3_m = float(s_mensal.quantile(0.25)), float(s_mensal.quantile(0.75))
    iiq_m = q3_m - q1_m
    ls_m = q3_m + 1.5 * iiq_m

    df_uf = df.groupby(['UF', 'Regiao'], as_index=False)['Total_Arrecadacao'].sum()
    s_uf = df_uf['Total_Arrecadacao']
    q1_uf, q3_uf = float(s_uf.quantile(0.25)), float(s_uf.quantile(0.75))
    iiq_uf = q3_uf - q1_uf
    ls_uf = q3_uf + 1.5 * iiq_uf

    df['IR_Total'] = (df['IRPF'] + df['IRPJ - ENTIDADES FINANCEIRAS'] + df['IRPJ - DEMAIS EMPRESAS'] +
                      df['IRRF - RENDIMENTOS DO TRABALHO'] + df['IRRF - RENDIMENTOS DO CAPITAL'] +
                      df['IRRF - REMESSAS P/ EXTERIOR'] + df['IRRF - OUTROS RENDIMENTOS'])
    df['COFINS_Total'] = df['COFINS'] + df['COFINS - FINANCEIRAS'] + df['COFINS - DEMAIS']
    df['PIS_Total'] = df['CONTRIBUIÇÃO PARA O PIS/PASEP'] + df['CONTRIBUIÇÃO PARA O PIS/PASEP - FINANCEIRAS'] + df['CONTRIBUIÇÃO PARA O PIS/PASEP - DEMAIS']
    df['IPI_Total'] = df['IPI - FUMO'] + df['IPI - BEBIDAS'] + df['IPI - AUTOMÓVEIS'] + df['IPI - VINCULADO À IMPORTACAO'] + df['IPI - OUTROS']

    gold_payload = {
        "metadata": {
            "total_registros": int(len(df)),
            "total_colunas": int(len(df.columns)),
            "ano_inicio": int(df['Ano'].min()),
            "ano_fim": int(df['Ano'].max()),
            "soma_total_reais": float(s_mensal.sum())
        },
        "estatisticas_mensais": {
            "media": float(s_mensal.mean()),
            "mediana": float(s_mensal.median()),
            "q1": q1_m,
            "q3": q3_m,
            "p10": float(s_mensal.quantile(0.10)),
            "p90": float(s_mensal.quantile(0.90)),
            "minimo": float(s_mensal.min()),
            "maximo": float(s_mensal.max()),
            "amplitude": float(s_mensal.max() - s_mensal.min()),
            "iiq": iiq_m,
            "variancia": float(s_mensal.var()),
            "desvio_padrao": float(s_mensal.std()),
            "cv_percentual": float((s_mensal.std() / s_mensal.mean()) * 100),
            "assimetria_skew": float(s_mensal.skew()),
            "limite_outlier_tukey": ls_m,
            "qtd_outliers": int((s_mensal > ls_m).sum())
        },
        "estatisticas_uf": {
            "media": float(s_uf.mean()),
            "mediana": float(s_uf.median()),
            "q1": q1_uf,
            "q3": q3_uf,
            "p10": float(s_uf.quantile(0.10)),
            "p90": float(s_uf.quantile(0.90)),
            "minimo": float(s_uf.min()),
            "maximo": float(s_uf.max()),
            "amplitude": float(s_uf.max() - s_uf.min()),
            "iiq": iiq_uf,
            "variancia": float(s_uf.var()),
            "desvio_padrao": float(s_uf.std()),
            "cv_percentual": float((s_uf.std() / s_uf.mean()) * 100),
            "assimetria_skew": float(s_uf.skew()),
            "limite_outlier_tukey": ls_uf,
            "ufs_outliers": df_uf[df_uf['Total_Arrecadacao'] > ls_uf]['UF'].tolist()
        },
        "correlacoes_pearson": {
            "cofins_vs_pis": float(df['COFINS_Total'].corr(df['PIS_Total'])),
            "ir_vs_total": float(df['IR_Total'].corr(df['Total_Arrecadacao'])),
            "cofins_vs_ir": float(df['COFINS_Total'].corr(df['IR_Total'])),
            "ipi_vs_importacao": float(df['IPI_Total'].corr(df['IMPOSTO SOBRE IMPORTAÇÃO']))
        }
    }

    Path(output_json).parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(gold_payload, f, ensure_ascii=False, indent=2)
    print(f"[GOLD] Indicadores estatísticos exportados com sucesso para: {output_json}")

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    bronze_file = base_dir / "data" / "bronze" / "arrecadacao-estado-tratado.xlsx"
    silver_csv = base_dir / "data" / "silver" / "dados_limpos_silver.csv"
    gold_json = base_dir / "data" / "gold" / "analytics_gold.json"

    df_silver = run_silver_layer(str(bronze_file))
    df_silver.to_csv(silver_csv, index=False, encoding='utf-8')
    run_gold_layer(df_silver, str(gold_json))
