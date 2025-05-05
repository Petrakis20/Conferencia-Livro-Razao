import streamlit as st
import pandas as pd
from cfop import CFOP_DATA  # estrutura reorganizada CFOP

# Mapas de CFOP de entrada e saída
entrada_cfop = CFOP_DATA.get('ENTRADA', {})
saida_cfop = CFOP_DATA.get('SAIDA', {})

# Função para extrair valores por CFOP dos livros fiscais
def extract_values(file) -> pd.DataFrame:
    df = pd.read_excel(file, dtype=str)
    cfop_col, val_col = 'CFOP', 'Valor Contábil'
    if cfop_col not in df.columns or val_col not in df.columns:
        return pd.DataFrame(columns=['CFOP', 'Valor Contábil'])
    df_sel = df[[cfop_col, val_col]].copy()
    df_sel['CFOP'] = df_sel[cfop_col].astype(str).str.zfill(4)
    df_sel['Valor Contábil'] = pd.to_numeric(df_sel[val_col], errors='coerce').fillna(0)
    df_group = df_sel.groupby('CFOP', as_index=False)['Valor Contábil'].sum()
    return df_group

# Função para extrair lançamentos detalhados do razão contábil usando Valor Absoluto
def extract_razao(file) -> pd.DataFrame:
    xls = pd.ExcelFile(file)
    records = []
    cols_needed = ['Lançamento automático', 'Contrapartida', 'Valor Absoluto', 'C/D', 'Descrição']
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet, dtype=str)
        df.columns = df.columns.str.strip()
        # verifica se colunas existentes
        if not all(col in df.columns for col in cols_needed):
            continue
        df_sel = df[cols_needed].copy()
        # converte e ajusta sinal
        df_sel['Valor'] = pd.to_numeric(df_sel['Valor Absoluto'], errors='coerce').fillna(0)
        df_sel.loc[df_sel['C/D'].str.upper() == 'C', 'Valor'] *= -1
        df_sel = df_sel.rename(columns={'Valor Absoluto': 'Valor Absoluto Original'})
        df_sel['Sheet'] = sheet
        records.append(df_sel[['Lançamento automático', 'Contrapartida', 'Valor', 'C/D', 'Descrição', 'Sheet']])
    if not records:
        return pd.DataFrame(columns=['Lançamento automático', 'Contrapartida', 'Valor', 'C/D', 'Descrição', 'Sheet'])
    return pd.concat(records, ignore_index=True)

# Função para extrair valores absolutos agrupados do razão contábil
# Agrupa por Lançamento automático ou Descrição e soma Valor Absoluto ajustado por C/D
def extract_abs_grouped(file) -> pd.DataFrame:
    xls = pd.ExcelFile(file)
    records = []
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet, dtype=str)
        df.columns = df.columns.str.strip()
        cols_lower = {c.lower(): c for c in df.columns}
        required = ['lançamento automático', 'contrapartida', 'descrição', 'valor absoluto', 'c/d']
        if not all(req in cols_lower for req in required):
            continue
        la = cols_lower['lançamento automático']
        cont = cols_lower['contrapartida']
        desc = cols_lower['descrição']
        val = cols_lower['valor absoluto']
        cd  = cols_lower['c/d']
        df2 = df[[la, cont, desc, val, cd]].copy()
        df2.columns = ['Lançamento automático', 'Contrapartida', 'Descrição', 'Valor Absoluto', 'C/D']
        df2['Valor Absoluto'] = pd.to_numeric(df2['Valor Absoluto'], errors='coerce').fillna(0)
        df2.loc[df2['C/D'].str.upper() == 'C', 'Valor Absoluto'] *= -1
        df2['GroupKey'] = df2['Lançamento automático'].fillna('').str.strip()
        df2['GroupKey'] = df2['GroupKey'].where(df2['GroupKey'] != '', df2['Descrição'])
        records.append(df2)
    if not records:
        return pd.DataFrame(columns=['Lançamento automático', 'Contrapartida', 'Descrição', 'Valor Absoluto Total'])
    all_df = pd.concat(records, ignore_index=True)
    grouped = all_df.groupby('GroupKey', as_index=False)['Valor Absoluto'].sum().rename(columns={'Valor Absoluto': 'Valor Absoluto Total'})
    results = []
    for _, row in grouped.iterrows():
        key = row['GroupKey']
        total = row['Valor Absoluto Total']
        subset = all_df[all_df['GroupKey'] == key]
        la_vals = subset['Lançamento automático'].dropna().unique()
        la_auto = la_vals[0] if len(la_vals) else ''
        contr_mode = subset['Contrapartida'].mode()
        contr = contr_mode.iloc[0] if not contr_mode.empty else ''
        desc_mode = subset['Descrição'].mode()
        descricao = desc_mode.iloc[0] if not desc_mode.empty else ''
        results.append({
            'Lançamento automático': la_auto,
            'Contrapartida': contr,
            'Descrição': descricao,
            'Valor Absoluto Total': total
        })
    return pd.DataFrame(results)

# Configuração da página
st.set_page_config(page_title="Conferência Livro vs Razão", layout="wide")

st.title("📊 Conferência de Livros Fiscais e Razão Contábil")

st.markdown("""
Carregue abaixo:
- **Livro Fiscal de Entrada** e **Saída** para extrair valores por CFOP;
- **Razão Contábil** para extrair lançamentos detalhados e valores absolutos agrupados.
""")

# Upload e extração dos livros fiscais
col1, col2 = st.columns(2)
with col1:
    file_in = st.file_uploader("📥 Livro Fiscal - Entrada", type=["xls","xlsx"], key="in")
    if file_in:
        df_in = extract_values(file_in)
        st.subheader("Resultados - Livro Fiscal de Entrada")
        st.table(df_in)
with col2:
    file_out = st.file_uploader("📤 Livro Fiscal - Saída", type=["xls","xlsx"], key="out")
    if file_out:
        df_out = extract_values(file_out)
        st.subheader("Resultados - Livro Fiscal - Saída")
        st.table(df_out)

# Upload e extração do razão contábil
def _process_razao():
    file_razao = st.file_uploader("📖 Razão Contábil", type=["xls","xlsx"], key="razao")
    if not file_razao:
        return
    df_razao = extract_razao(file_razao)
    st.subheader("Resultados - Razão Contábil (Detalhado)")
    st.table(df_razao)
    df_abs = extract_abs_grouped(file_razao)
    st.subheader("Valores Absolutos Agrupados")
    st.table(df_abs)
_process_razao()

# Sidebar de instruções
st.sidebar.header("Ajuda")
st.sidebar.markdown(
    "- Faça upload dos livros fiscais para ver CFOP vs Valores. \n"
    " - Faça upload do razão contábil para ver lançamentos detalhados e valores absolutos agrupados."
)
