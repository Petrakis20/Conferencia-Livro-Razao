import streamlit as st
import pandas as pd
from cfop import CFOP_DATA  # estrutura reorganizada CFOP

# Mapas de CFOP de entrada e saída
entrada_cfop = CFOP_DATA.get('ENTRADA', {})
saida_cfop   = CFOP_DATA.get('SAIDA',   {})

# extrai valores por CFOP dos livros fiscais
def extract_values(file) -> pd.DataFrame:
    df = pd.read_excel(file, dtype=str)
    cfop_col, val_col = 'CFOP', 'Valor Contábil'
    if cfop_col not in df.columns or val_col not in df.columns:
        return pd.DataFrame(columns=['CFOP', 'Valor Contábil'])
    df_sel = df[[cfop_col, val_col]].copy()
    df_sel['CFOP'] = df_sel[cfop_col].astype(str).str.zfill(4)
    df_sel['Valor Contábil'] = pd.to_numeric(df_sel[val_col], errors='coerce').fillna(0)
    return df_sel.groupby('CFOP', as_index=False)['Valor Contábil'].sum()

# extrai lançamentos detalhados do razão
def extract_razao(file) -> pd.DataFrame:
    xls = pd.ExcelFile(file)
    recs = []
    need = ['Lançamento automático','Contrapartida','Valor Absoluto','C/D','Descrição']
    for sh in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sh, dtype=str)
        df.columns = df.columns.str.strip()
        if not all(c in df.columns for c in need):
            continue
        sel = df[need].copy()
        sel['Valor'] = pd.to_numeric(sel['Valor Absoluto'], errors='coerce').fillna(0)
        sel.loc[sel['C/D'].str.upper()=='C','Valor'] *= -1
        sel['Sheet'] = sh
        recs.append(sel.rename(columns={'Valor Absoluto':'Valor Absoluto Original'})[[
            'Lançamento automático','Contrapartida','Valor','C/D','Descrição','Sheet'
        ]])
    if not recs:
        return pd.DataFrame(columns=['Lançamento automático','Contrapartida','Valor','C/D','Descrição','Sheet'])
    return pd.concat(recs, ignore_index=True)

# agrupa sempre por Lançamento automático e soma os valores
def extract_abs_grouped(file) -> pd.DataFrame:
    xls = pd.ExcelFile(file)
    recs = []
    for sh in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sh, dtype=str)
        df.columns = df.columns.str.strip()
        cols = {c.lower():c for c in df.columns}
        req = ['lançamento automático','valor absoluto','c/d','contrapartida','descrição']
        if not all(r in cols for r in req):
            continue
        la = cols['lançamento automático']
        val = cols['valor absoluto']
        cd = cols['c/d']
        df2 = df[[la,val,cd]].copy()
        df2.columns = ['Lançamento automático','Valor Absoluto','C/D']
        df2['Valor Absoluto'] = pd.to_numeric(df2['Valor Absoluto'], errors='coerce').fillna(0)
        df2.loc[df2['C/D'].str.upper()=='C','Valor Absoluto'] *= -1
        recs.append(df2[['Lançamento automático','Valor Absoluto']])
    if not recs:
        return pd.DataFrame(columns=['Lançamento automático','Valor Absoluto Total'])
    all_df = pd.concat(recs, ignore_index=True)
    # mantém só lançamentos automáticos preenchidos
    all_df['Lançamento automático'] = all_df['Lançamento automático'].fillna('').astype(str).str.strip()
    all_df = all_df[all_df['Lançamento automático']!='']
    # soma por lançamento automático
    return (
        all_df
        .groupby('Lançamento automático', as_index=False)['Valor Absoluto']
        .sum()
        .rename(columns={'Valor Absoluto':'Valor Absoluto Total'})
    )

# monta comparativo CFOP × razão
def build_comparativo(df_abs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df_abs.iterrows():
        la = r['Lançamento automático']
        val = r['Valor Absoluto Total']
        found = False
        for grp in ('ENTRADA','SAIDA'):
            for cfop, info in CFOP_DATA.get(grp,{}).items():
                for tipo in ('contabil','icms','ipi','icms_st'):
                    if info.get(tipo,{}).get(f'la_{tipo}') == la:
                        rows.append({
                            'Lançamento automático': la,
                            'CFOP': cfop,
                            'Tipo': tipo,
                            'Valor Absoluto Total': val
                        })
                        found = True
        if not found:
            rows.append({
                'Lançamento automático': la,
                'CFOP': '',
                'Tipo': 'não mapeado',
                'Valor Absoluto Total': val
            })
    return pd.DataFrame(rows)

# === Streamlit ===
st.set_page_config(page_title="Conferência Livro vs Razão", layout="wide")
st.title("📊 Conferência de Livros Fiscais e Razão Contábil")
st.markdown("""
- Carregue **Livro Fiscal Entrada/Saída** para extrair CFOP × Valor;
- Carregue **Razão Contábil** para extrair valores agrupados por lançamento automático e comparar com CFOP.
""")

c1, c2 = st.columns(2)
with c1:
    f_in = st.file_uploader("📥 Livro Fiscal - Entrada", type=["xls","xlsx"], key="in")
    if f_in:
        df_in = extract_values(f_in)
        st.subheader("Resultado - Entrada")
        st.table(df_in)
with c2:
    f_out = st.file_uploader("📤 Livro Fiscal - Saída", type=["xls","xlsx"], key="out")
    if f_out:
        df_out = extract_values(f_out)
        st.subheader("Resultado - Saída")
        st.table(df_out)

f_razao = st.file_uploader("📖 Razão Contábil", type=["xls","xlsx"], key="razao")
if f_razao:
    st.subheader("Razão (detalhado)")
    st.table(extract_razao(f_razao))
    st.subheader("Valores Absolutos Agrupados por Lançamento Automático")
    df_abs = extract_abs_grouped(f_razao)
    st.table(df_abs)
    st.subheader("Comparativo CFOP × Razão")
    st.table(build_comparativo(df_abs))

st.sidebar.header("Ajuda")
st.sidebar.markdown(
    "- Faça upload dos livros fiscais.\n"
    "- Faça upload do razão contábil para ver os valores já somados por lançamento automático e compará-los com o CFOP."
)
