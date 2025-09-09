import streamlit as st
import pandas as pd
from cfop import CFOP_DATA
import os

# ——— 1) Construção dos dicionários invertidos CFOP ← la_contabil ———

entrada_rev = {}
for cfop, d in CFOP_DATA['ENTRADA'].items():
    la = d['contabil']['la_contabil']
    if la not in (None, '', 0):
        chave = str(la)
        entrada_rev.setdefault(chave, []).append(cfop)

saida_rev = {}
for cfop, d in CFOP_DATA['SAIDA'].items():
    la = d['contabil']['la_contabil']
    if la not in (None, '', 0):
        chave = str(la)
        saida_rev.setdefault(chave, []).append(cfop)

def _open_excel(file):
    """Abre um pd.ExcelFile detectando xlsx/xlsb."""
    ext = os.path.splitext(file.name)[1].lower()
    if ext == '.xlsb':
        return pd.ExcelFile(file, engine='pyxlsb')
    else:
        return pd.ExcelFile(file)

# ——— 2) Extrai o BI (Entrada ou Saída), agrupando por Lançamento, CFOP e somando Valor Contábil
def extract_book(file) -> pd.DataFrame:
    launch_col = 'Lanc. Cont. Vl. Contábil'
    cfop_col   = 'CFOP'
    val_col    = 'Valor Contábil'

    xls = _open_excel(file)
    recs = []
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet, dtype=str, engine=xls.engine)
        if any(c not in df.columns for c in (launch_col, cfop_col, val_col)):
            continue
        tmp = df[[launch_col, cfop_col, val_col]].copy()
        tmp[launch_col] = tmp[launch_col].astype(str).str.strip()
        tmp['CFOP']     = tmp[cfop_col].astype(str).str.zfill(4)
        tmp[val_col]    = pd.to_numeric(tmp[val_col], errors='coerce').fillna(0)
        tmp['Sheet']    = sheet
        recs.append(tmp[[launch_col, 'CFOP', val_col, 'Sheet']])

    if not recs:
        return pd.DataFrame(columns=[launch_col, 'CFOP', 'Valor Contábil Total', 'Sheet'])

    all_df = pd.concat(recs, ignore_index=True)
    df_sum = (
        all_df
        .groupby([launch_col, 'CFOP'], as_index=False)[val_col]
        .sum()
        .rename(columns={val_col: 'Valor Contábil Total'})
    )
    df_sheets = (
        all_df
        .groupby(launch_col)['Sheet']
        .unique()
        .apply(lambda arr: '/'.join(arr))
        .reset_index(name='Sheets')
    )
    return df_sum.merge(df_sheets, on=launch_col)

# ——— 3) Extrai o Razão Contábil, agrupando Valor Absoluto por Lançamento e listando sheets
def extract_razao_abs(file) -> pd.DataFrame:
    xls = _open_excel(file)
    recs = []
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet, dtype=str, engine=xls.engine)
        df.columns = df.columns.str.strip()
        cols = {c.lower(): c for c in df.columns}
        if not all(k in cols for k in ('lançamento automático','valor absoluto','c/d')):
            continue

        tmp = df[[cols['lançamento automático'], cols['valor absoluto'], cols['c/d']]].copy()
        tmp.columns = ['Lançamento automático','Valor Absoluto','C/D']
        tmp['Valor Absoluto'] = pd.to_numeric(tmp['Valor Absoluto'], errors='coerce').fillna(0)
        tmp.loc[tmp['C/D'].str.upper() == 'C','Valor Absoluto'] *= -1
        tmp['Sheet'] = sheet
        recs.append(tmp[['Lançamento automático','Valor Absoluto','Sheet']])

    if not recs:
        return pd.DataFrame(columns=['Lançamento automático','Valor Absoluto Total','Sheets'])

    all_df = pd.concat(recs, ignore_index=True)
    df_sum = (
        all_df
        .groupby('Lançamento automático', as_index=False)['Valor Absoluto']
        .sum()
        .rename(columns={'Valor Absoluto':'Valor Absoluto Total'})
    )
    df_sheets = (
        all_df
        .groupby('Lançamento automático')['Sheet']
        .unique()
        .apply(lambda arr: '/'.join(arr))
        .reset_index(name='Sheets')
    )
    return df_sum.merge(df_sheets, on='Lançamento automático')

# ——— 4) Interface Streamlit ———

st.set_page_config(page_title="Conferência Livro vs Razão", layout="wide")
st.title("📊 Conferência Livro Fiscal × Razão Contábil")

st.markdown("""
1. Carregue o **BI (Entrada/Saída)**: agrupa `Valor Contábil` por `Lançamento automático + CFOP` e mostra a aba fonte.  
2. Carregue o **Razão Contábil**: agrupa `Valor Absoluto` por `Lançamento automático` e lista as abas.
3. Para cada lançamento, comparamos lado-a-lado (BI ↔ Razão).
""")

col1, col2 = st.columns(2)
df_in = df_out = df_abs = None

with col1:
    arquivo_in = st.file_uploader("📥 BI Entrada", type=["xls","xlsx","xlsb"], key="in")
    if arquivo_in:
        df_in = extract_book(arquivo_in)
        st.subheader("BI Entrada (agrupado)")
        st.dataframe(df_in.style.format({"Valor Contábil Total":"{:,.2f}"}))

with col2:
    arquivo_out = st.file_uploader("📤 BI Saída", type=["xls","xlsx","xlsb"], key="out")
    if arquivo_out:
        df_out = extract_book(arquivo_out)
        st.subheader("BI Saída (agrupado)")
        st.dataframe(df_out.style.format({"Valor Contábil Total":"{:,.2f}"}))

arquivo_razao = st.file_uploader("📖 Razão Contábil", type=["xls","xlsx","xlsb"], key="razao")
if arquivo_razao:
    df_abs = extract_razao_abs(arquivo_razao)
    st.subheader("Razão Contábil (agrupado)")
    st.dataframe(df_abs.style.format({"Valor Absoluto Total":"{:,.2f}"}))

    def comparativo(df_book, rev_map, titulo):
        launch_col = 'Lanc. Cont. Vl. Contábil'
        st.subheader(titulo)

        for la in df_book[launch_col].unique():
            # BI detalhe
            df_book_det = df_book[df_book[launch_col]==la][['CFOP','Valor Contábil Total','Sheets']]
            total_book = df_book_det['Valor Contábil Total'].sum()

            # razão correspondente
            abs_row = df_abs[df_abs['Lançamento automático']==la]
            total_abs = float(abs_row['Valor Absoluto Total']) if not abs_row.empty else 0
            cfops = rev_map.get(str(la), [])
            sheets_razao = abs_row['Sheets'].iloc[0] if not abs_row.empty else ''

            status = "OK" if abs(total_book - total_abs) < 1e-2 else "DIFERENTE"

            st.markdown(f"### Lançamento Automático: {la} — **{status}**")
            c1, c2 = st.columns(2)

            with c1:
                st.markdown("**Livro Fiscal**")
                st.table(
                    df_book_det.assign(**{
                        "Valor Contábil Total": df_book_det["Valor Contábil Total"].map("{:,.2f}".format)
                    })
                )
                st.markdown(f"**Total BI:** {total_book:,.2f}")

            with c2:
                st.markdown("**Razão Contábil**")
                df_rz = pd.DataFrame([{
                    "CFOPs encontrados": " / ".join(cfops),
                    "Sheets": sheets_razao,
                    "Valor Absoluto Total": f"{total_abs:,.2f}"
                }])
                st.table(
                    df_rz.style.applymap(
                        lambda _: "color:red" if status=="DIFERENTE" else "",
                        subset=["Valor Absoluto Total"]
                    )
                )

    if df_in is not None:
        comparativo(df_in, entrada_rev, "📈 Comparativo Entrada × Razão")
    if df_out is not None:
        comparativo(df_out, saida_rev, "📉 Comparativo Saída × Razão")

st.sidebar.header("Ajuda")
st.sidebar.markdown("""
- Agora aceita arquivos `.xlsb` também.  
- O campo **Sheets** mostra de qual aba vieram as linhas.  
- Valores divergentes no Razão aparecem em **vermelho**.
""")
