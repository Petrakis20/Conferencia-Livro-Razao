import streamlit as st
import pandas as pd
from cfop import CFOP_DATA  # sua estrutura reorganizada de CFOPs

# Mapas de CFOP de entrada e saída
entrada_cfop = CFOP_DATA.get('ENTRADA', {})
saida_cfop = CFOP_DATA.get('SAIDA', {})

# --- FUNÇÕES DE EXTRAÇÃO ---------------------------------------------------

def extract_values(file) -> pd.DataFrame:
    """Extrai e soma valor contábil por CFOP de um livro fiscal."""
    df = pd.read_excel(file, dtype=str)
    cfop_col, val_col = 'CFOP', 'Valor Contábil'
    if cfop_col not in df.columns or val_col not in df.columns:
        return pd.DataFrame(columns=['CFOP', 'Valor Contábil'])
    df_sel = df[[cfop_col, val_col]].copy()
    df_sel['CFOP'] = df_sel[cfop_col].astype(str).str.zfill(4)
    df_sel['Valor Contábil'] = pd.to_numeric(df_sel[val_col], errors='coerce').fillna(0)
    return df_sel.groupby('CFOP', as_index=False)['Valor Contábil'].sum()

def extract_razao(file) -> pd.DataFrame:
    """Extrai o detalhamento bruto do razão contábil."""
    xls = pd.ExcelFile(file)
    records = []
    cols = ['Lançamento automático', 'Contrapartida', 'Valor Absoluto', 'C/D', 'Descrição']
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet, dtype=str)
        df.columns = df.columns.str.strip()
        if not all(c in df.columns for c in cols):
            continue
        df_sel = df[cols].copy()
        df_sel['Valor'] = pd.to_numeric(df_sel['Valor Absoluto'], errors='coerce').fillna(0)
        df_sel.loc[df_sel['C/D'].str.upper() == 'C', 'Valor'] *= -1
        df_sel['Sheet'] = sheet
        records.append(df_sel)
    if not records:
        return pd.DataFrame(columns=cols + ['Valor', 'Sheet'])
    return pd.concat(records, ignore_index=True)

def extract_abs_grouped(file) -> pd.DataFrame:
    """
    Agrupa por Lançamento automático (ou Descrição, se vazio) e soma o Valor Ajustado,
    retornando Lançamento automático, Contrapartida, Descrição e Valor Absoluto Total.
    """
    xls = pd.ExcelFile(file)
    records = []
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet, dtype=str)
        df.columns = df.columns.str.strip()
        lower_map = {c.lower(): c for c in df.columns}
        req = ['lançamento automático', 'contrapartida', 'descrição', 'valor absoluto', 'c/d']
        if not all(r in lower_map for r in req):
            continue
        la = lower_map['lançamento automático']
        cont = lower_map['contrapartida']
        desc = lower_map['descrição']
        val = lower_map['valor absoluto']
        cd  = lower_map['c/d']
        df2 = df[[la, cont, desc, val, cd]].copy()
        df2.columns = ['Lançamento automático', 'Contrapartida', 'Descrição', 'Valor Absoluto', 'C/D']
        df2['Valor Absoluto'] = pd.to_numeric(df2['Valor Absoluto'], errors='coerce').fillna(0)
        df2.loc[df2['C/D'].str.upper() == 'C', 'Valor Absoluto'] *= -1
        # cria chave de agrupamento
        df2['GroupKey'] = df2['Lançamento automático'].fillna('').str.strip()
        df2['GroupKey'] = df2['GroupKey'].where(df2['GroupKey'] != '', df2['Descrição'])
        records.append(df2)
    if not records:
        return pd.DataFrame(columns=['Lançamento automático', 'Contrapartida', 'Descrição', 'Valor Absoluto Total'])
    all_df = pd.concat(records, ignore_index=True)
    grouped = (
        all_df
        .groupby('GroupKey', as_index=False)['Valor Absoluto']
        .sum()
        .rename(columns={'Valor Absoluto': 'Valor Absoluto Total'})
    )
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

def process_comparativo(df_book: pd.DataFrame, df_abs: pd.DataFrame, cfop_map: dict, mode_label: str):
    """
    Para cada lançamento automático em df_abs, exibe:
      - à esquerda: tabela de CFOPs do livro fiscal + soma
      - à direita: CFOPs unificados da razão + valor absoluto total (pintado se discrepante)
    """
    st.subheader(f"Comparativo — {mode_label}")
    for _, row in df_abs.iterrows():
        la = row['Lançamento automático']
        valor_razao = row['Valor Absoluto Total']
        contr = row['Contrapartida']
        # identifica todos os CFOPs que têm esse lançamento automático em algum tipo
        cfops = [
            cfop
            for cfop, tipos in cfop_map.items()
            for tipo, d in tipos.items()
            if d.get(f'la_{tipo}') == la
        ]
        # filtra o livro fiscal
        df_fiscal = df_book[df_book['CFOP'].isin(cfops)].copy()
        total_fiscal = df_fiscal['Valor Contábil'].sum()
        # cor de status
        diff = abs(total_fiscal - valor_razao)
        status = "🔴" if diff > 1e-2 else "🟢"

        with st.expander(f"Lançamento Automático: {la}", expanded=True):
            left, right = st.columns(2)
            with left:
                st.markdown("**Livro Fiscal**")
                if df_fiscal.empty:
                    st.write("_nenhum CFOP encontrado_")
                else:
                    st.table(df_fiscal)
                st.markdown(f"**Total Livro:** R$ {total_fiscal:,.2f}")
            with right:
                st.markdown("**Razão Contábil**")
                st.markdown(f"- **CFOPs:** {' / '.join(cfops) if cfops else '_nenhum_'}  ")
                st.markdown(f"- **Contrapartida:** {contr or '-'}  ")
                st.markdown(f"- **Valor Razão:** R$ {valor_razao:,.2f} {status}")

# --- FLUXO PRINCIPAL STREAMLIT ---------------------------------------------

st.set_page_config(page_title="Conferência Livro vs Razão", layout="wide")
st.title("📊 Conferência de Livros Fiscais e Razão Contábil")
st.markdown("""
Carregue abaixo:
- **Livro Fiscal de Entrada** e **Saída** para extrair valores por CFOP;
- **Razão Contábil** para extrair lançamentos detalhados e valores absolutos agrupados.
""")

# upload dos livros fiscais
col1, col2 = st.columns(2)
df_in = df_out = None
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
        st.subheader("Resultados - Livro Fiscal de Saída")
        st.table(df_out)

# upload e processamento do razão contábil + comparativo
file_razao = st.file_uploader("📖 Razão Contábil", type=["xls","xlsx"], key="razao")
if file_razao:
    df_razao = extract_razao(file_razao)
    st.subheader("Resultados - Razão Contábil (Detalhado)")
    st.table(df_razao)

    df_abs = extract_abs_grouped(file_razao)
    st.subheader("Valores Absolutos Agrupados")
    st.table(df_abs)

    # exibe comparativo para Entrada e Saída
    if df_in is not None:
        process_comparativo(df_in, df_abs, entrada_cfop, "Entrada")
    if df_out is not None:
        process_comparativo(df_out, df_abs, saida_cfop, "Saída")

# sidebar de ajuda
st.sidebar.header("Ajuda")
st.sidebar.markdown(
    "- Faça upload dos livros fiscais para ver CFOP vs Valores.\n"
    "- Faça upload do razão contábil para ver detalhes e comparativos."
)
