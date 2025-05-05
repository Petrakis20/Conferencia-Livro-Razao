import pandas as pd

def clean_cell(val):
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.lower() in {"não possui", "x"}:
        return ""
    try:
        return int(float(s))
    except ValueError:
        return s

def build_cfop_dict(df):
    # Assumindo que em df.columns já foi aplicado strip().upper()
    result = {}
    for _, row in df.iterrows():
        cfop = str(row['CFOP']).strip()
        result[cfop] = {
            'contabil': {
                'la_contabil': clean_cell(row.get('L.A. CONTÁBIL')),
                'd_contabil':  clean_cell(row.get('DÉBITO CONTÁBIL')),
                'c_contabil':  clean_cell(row.get('CRÉDITO CONTÁBIL')),
            },
            'icms': {
                'la_icms': clean_cell(row.get('L.A. ICMS')),
                'd_icms':  clean_cell(row.get('DÉBITO ICMS')),
                'c_icms':  clean_cell(row.get('CRÉDITO ICMS')),
            },
            'ipi': {
                'la_ipi': clean_cell(row.get('L.A. IPI')),
                'd_ipi':  clean_cell(row.get('DÉBITO IPI')),
                'c_ipi':  clean_cell(row.get('CRÉDITO IPI')),
            },
            'icms_st': {
                'la_icms_st': clean_cell(row.get('L.A. ICMS ST')),
                'd_icms_st':  clean_cell(row.get('DÉBITO ICMS ST')),
                'c_icms_st':  clean_cell(row.get('CRÉDITO ICMS ST')),
            },
        }
    return result

def main():
    file_path = 'Tabela CFOP - organizada.xlsx'  # ajuste conforme seu ambiente
    sheets = {
        'ENTRADA': 'CFOP - ENTRADA',
        'SAIDA':   'CFOP - SAÍDA'
    }

    cfop_data = {}
    for key, sheet_name in sheets.items():
        # lê a planilha
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        # normaliza colunas (strip + uppercase)
        df.columns = (
            df.columns
              .str.strip()
              .str.upper()
              .str.replace(r'\s+', ' ', regex=True)  # opcional: reduz espaços múltiplos
        )
        # debug rápido: confira os nomes carregados
        print(f"[{key}] colunas:", df.columns.tolist())
        cfop_data[key] = build_cfop_dict(df)

    # Exemplo de saída:
    # print(cfop_data['ENTRADA']['1101'])
    # print(cfop_data['SAIDA']['1101'])
    return cfop_data

if __name__ == "__main__":
    data = main()
    import pprint
    pprint.pprint(data)
