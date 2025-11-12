"""
Módulo de conexão e extração de dados do Alterdata (SQL Server).
Responsável por conectar ao banco de dados e executar queries de BI.
"""

import os
import pyodbc
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import streamlit as st
from dotenv import load_dotenv


# Carrega credenciais do .env
ENV_PATH = Path("Alterdata_BI/.env")
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


def get_db_credentials() -> Tuple[str, str, str, str]:
    """
    Obtém credenciais do banco de dados do arquivo .env.

    Returns:
        Tupla (host, database, user, password)
    """
    host = os.getenv("DB_HOST", "")
    database = os.getenv("DB_NAME", "")
    user = os.getenv("DB_USER", "")
    password = os.getenv("DB_PASS", "").strip("'\"")  # Remove aspas se houver

    return host, database, user, password


# Queries SQL (adaptadas do queries.js do Node.js)
QUERY_SAIDA = """
SELECT DISTINCT
    CAST(CASE WHEN M.StCancelada = 'S' THEN 'Sim' ELSE 'Não' END AS VARCHAR(3)) AS [Cancelada],
    M.dtEscrituracao AS [Dt. Escrituração],
    M.DtEmissao AS [Data Emissão],
    M.IdCodFiscal AS [CFOP],
    CAST(CASE
        WHEN CFOP.CdTipo = 'C' AND M.StTipo = 'E' THEN 'Compras Normais'
        WHEN CFOP.CdTipo = 'C' AND M.StTipo = 'S' THEN 'Vendas Normais'
        WHEN CFOP.CdTipo = 'T' THEN 'Transferências'
        WHEN CFOP.CdTipo = 'D' THEN 'Devoluções'
        WHEN CFOP.CdTipo = 'E' THEN 'Energia Elétrica'
        WHEN CFOP.CdTipo = 'U' THEN 'Uso e Consumo'
        WHEN CFOP.CdTipo = 'A' THEN 'Ativo Imobilizado'
        WHEN CFOP.CdTipo = 'M' THEN 'Comunicações'
        WHEN CFOP.CdTipo = 'R' THEN 'Transportes'
        WHEN CFOP.CdTipo = 'O' THEN 'Outros'
        WHEN CFOP.CdTipo = 'X' THEN 'Exportação'
        WHEN CFOP.CdTipo = 'I' THEN 'Importação'
        WHEN CFOP.CdTipo = 'S' THEN 'Subst. Tributária'
        WHEN CFOP.CdTipo = 'N' THEN 'Transf. Ativo'
        WHEN CFOP.CdTipo = 'F' THEN 'Transf. Uso Cons.'
        WHEN CFOP.CdTipo = '.' THEN 'Transf. Crédito'
        ELSE '' END AS VARCHAR(30)) AS [Tipo CFOP],
    M.NmNumero AS [Número],
    F.NmNome AS [Nome Forn/Cliente],
    M.VlContabil AS [Valor Contábil],
    ROUND(COALESCE(M.VlICMSValor,0), 2) AS [Vl. ICMS],
    M.VlValorST AS [Vl. ST],
    M.VlIPIValor AS [Vl. IPI],
    M.IdTipoOperacao AS [Cód. Oper. Contábil],
    M.IdLancContabil AS [Lanc. Cont. Vl. Contábil],
    M.IdLancIcms AS [Lanc. Cont. Vl. ICMS],
    M.IdLancIcmsST AS [Lanc. Cont. Vl. Subst. Trib.],
    M.IdLancIpi AS [Lanc. Cont. Vl. IPI],
    CAST(CASE
        WHEN COALESCE(CASE WHEN ZOP.Exportado = CAST(1 AS bit) THEN 'S' ELSE M.StExportado END,'N')='S'
        THEN 'Sim' ELSE 'Não' END AS VARCHAR(3)) AS [Exportado],
    M.VlBaseST AS [Base ST],
    COALESCE(M.Total_Pis_Unidade_Medida,0) + COALESCE(M.Total_Pis_Cumulativo,0) + COALESCE(M.Total_Pis_Nao_Cumulativo,0) AS [Total PIS],
    COALESCE(M.Total_Cofins_Unidade_Medida,0) + COALESCE(M.Total_Cofins_Cumulativo,0) + COALESCE(M.Total_Cofins_Nao_Cumulativo,0) AS [Total CONFINS],
    M.VlIPIBase AS [Vl. Base IPI],
    M.VlIPIAliquota AS [% IPI],
    M.VlIPINaoAproveitado AS [IPI Não Aproveitado],
    M.VlICMSBase AS [Vl. Base ICMS],
    M.VlICMSAliquota AS [%ICMS],
    M.CSTICMS AS [CST ICMS],
    M.informacao_complementar AS [Informações Complementares],
    CONVERT(DATETIME, M.data_importacao) AS [Data da Importação],
    M.nome_usuario_importacao AS [Usuário Importador],
    F.CdCgc AS [CNPJ/CPF forn/Cliente],
    M.IdModDocFiscal AS [Mod.],
    M.chave_acesso_nota_eletronica AS [Chave de Acesso NFe/CF SAT]
FROM WFiscal.M{code5} M
LEFT JOIN WFISCAL.movimento_reducao_z Z ON Z.Data = M.DtEscrituracao AND Z.Ecf_Id = M.CodECF
LEFT JOIN WFISCAL.movimento_reducao_z_por_operacao ZOP ON ZOP.Movimento_Reducao_Z_Id = Z.Id AND ZOP.cfop = M.IdCodFiscal AND ZOP.aliquota_icms = M.VlICMSAliquota AND RIGHT(REPLICATE('0',3) + CAST(ZOP.cst_icms AS VARCHAR(3)), 3) = RIGHT(REPLICATE('0',3) + CAST(M.CSTICMS AS VARCHAR(3)), 3)
LEFT JOIN WFiscal.CadFisM CFOP ON M.IdCodFiscal = CFOP.IdCodigo
LEFT JOIN wfiscal.FORNEC F ON M.IdCodForCli = F.CdFornecedor
LEFT JOIN wphd.MunicipiosIBGE MUN ON (MUN.IdMunicipio = F.IdMunicipio AND M.TpEmissaoNF <> 'S') OR (MUN.IdMunicipio = ? AND M.TpEmissaoNF = 'S')
LEFT JOIN wfiscal.arquivos_xml_danfe X ON M.chave_acesso_nota_eletronica = X.id
LEFT JOIN WFiscal.MODDOC MD ON M.IdModDocFiscal = MD.CdCodigo
WHERE M.dtEscrituracao >= ? AND M.dtEscrituracao < ? AND M.StTipo = 'S' AND ISNULL(NULLIF(LTRIM(RTRIM(M.StCancelada)), ''), 'N') = 'N'
"""

QUERY_ENTRADA = """
SELECT DISTINCT
    CAST(CASE WHEN M.StCancelada = 'S' THEN 'Sim' ELSE 'Não' END AS VARCHAR(3)) AS [Cancelada],
    M.dtEscrituracao AS [Dt. Escrituração],
    M.DtEmissao AS [Data Emissão],
    M.IdCodFiscal AS [CFOP],
    CAST(CASE
        WHEN CFOP.CdTipo = 'C' AND M.StTipo = 'E' THEN 'Compras Normais'
        WHEN CFOP.CdTipo = 'C' AND M.StTipo = 'S' THEN 'Vendas Normais'
        WHEN CFOP.CdTipo = 'T' THEN 'Transferências'
        WHEN CFOP.CdTipo = 'D' THEN 'Devoluções'
        WHEN CFOP.CdTipo = 'E' THEN 'Energia Elétrica'
        WHEN CFOP.CdTipo = 'U' THEN 'Uso e Consumo'
        WHEN CFOP.CdTipo = 'A' THEN 'Ativo Imobilizado'
        WHEN CFOP.CdTipo = 'M' THEN 'Comunicações'
        WHEN CFOP.CdTipo = 'R' THEN 'Transportes'
        WHEN CFOP.CdTipo = 'O' THEN 'Outros'
        WHEN CFOP.CdTipo = 'X' THEN 'Exportação'
        WHEN CFOP.CdTipo = 'I' THEN 'Importação'
        WHEN CFOP.CdTipo = 'S' THEN 'Subst. Tributária'
        WHEN CFOP.CdTipo = 'N' THEN 'Transf. Ativo'
        WHEN CFOP.CdTipo = 'F' THEN 'Transf. Uso Cons.'
        WHEN CFOP.CdTipo = '.' THEN 'Transf. Crédito'
        ELSE '' END AS VARCHAR(30)) AS [Tipo CFOP],
    M.NmNumero AS [Número],
    F.NmNome AS [Nome Forn/Cliente],
    M.VlContabil AS [Valor Contábil],
    ROUND(COALESCE(M.VlICMSValor,0), 2) AS [Vl. ICMS],
    M.VlValorST AS [Vl. ST],
    M.VlIPIValor AS [Vl. IPI],
    M.IdTipoOperacao AS [Cód. Oper. Contábil],
    M.IdLancContabil AS [Lanc. Cont. Vl. Contábil],
    M.IdLancIcms AS [Lanc. Cont. Vl. ICMS],
    M.IdLancIcmsST AS [Lanc. Cont. Vl. Subst. Trib.],
    M.IdLancIpi AS [Lanc. Cont. Vl. IPI],
    CAST(CASE
        WHEN COALESCE(CASE WHEN ZOP.Exportado = CAST(1 AS bit) THEN 'S' ELSE M.StExportado END,'N')='S'
        THEN 'Sim' ELSE 'Não' END AS VARCHAR(3)) AS [Exportado],
    M.VlBaseST AS [Base ST],
    COALESCE(M.Total_Pis_Unidade_Medida,0) + COALESCE(M.Total_Pis_Cumulativo,0) + COALESCE(M.Total_Pis_Nao_Cumulativo,0) AS [Total PIS],
    COALESCE(M.Total_Cofins_Unidade_Medida,0) + COALESCE(M.Total_Cofins_Cumulativo,0) + COALESCE(M.Total_Cofins_Nao_Cumulativo,0) AS [Total CONFINS],
    M.VlIPIBase AS [Vl. Base IPI],
    M.VlIPIAliquota AS [% IPI],
    M.VlIPINaoAproveitado AS [IPI Não Aproveitado],
    M.VlICMSBase AS [Vl. Base ICMS],
    M.VlICMSAliquota AS [%ICMS],
    M.CSTICMS AS [CST ICMS],
    M.informacao_complementar AS [Informações Complementares],
    CONVERT(DATETIME, M.data_importacao) AS [Data da Importação],
    M.nome_usuario_importacao AS [Usuário Importador],
    F.CdCgc AS [CNPJ/CPF forn/Cliente],
    M.IdModDocFiscal AS [Mod.],
    M.chave_acesso_nota_eletronica AS [Chave de Acesso NFe/CF SAT]
FROM WFiscal.M{code5} M
LEFT JOIN WFISCAL.movimento_reducao_z Z ON Z.Data = M.DtEscrituracao AND Z.Ecf_Id = M.CodECF
LEFT JOIN WFISCAL.movimento_reducao_z_por_operacao ZOP ON ZOP.Movimento_Reducao_Z_Id = Z.Id AND ZOP.cfop = M.IdCodFiscal AND ZOP.aliquota_icms = M.VlICMSAliquota AND RIGHT(REPLICATE('0',3) + CAST(ZOP.cst_icms AS VARCHAR(3)), 3) = RIGHT(REPLICATE('0',3) + CAST(M.CSTICMS AS VARCHAR(3)), 3)
LEFT JOIN WFiscal.CadFisM CFOP ON M.IdCodFiscal = CFOP.IdCodigo
LEFT JOIN wfiscal.FORNEC F ON M.IdCodForCli = F.CdFornecedor
LEFT JOIN wphd.MunicipiosIBGE MUN ON (MUN.IdMunicipio = F.IdMunicipio AND M.TpEmissaoNF <> 'S') OR (MUN.IdMunicipio = ? AND M.TpEmissaoNF = 'S')
LEFT JOIN wfiscal.arquivos_xml_danfe X ON M.chave_acesso_nota_eletronica = X.id
LEFT JOIN WFiscal.MODDOC MD ON M.IdModDocFiscal = MD.CdCodigo
WHERE M.dtEscrituracao >= ? AND M.dtEscrituracao < ? AND M.StTipo = 'E' AND ISNULL(NULLIF(LTRIM(RTRIM(M.StCancelada)), ''), 'N') = 'N'
"""


def get_connection_string(host: str, database: str, user: str, password: str) -> str:
    """Constrói string de conexão para SQL Server."""
    # Tenta diferentes versões de driver ODBC (18, 17, 13)
    drivers = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 13 for SQL Server"
    ]

    # Testa qual driver está disponível
    import pyodbc
    available_drivers = [d for d in pyodbc.drivers() if 'SQL Server' in d]

    # Usa o primeiro driver disponível da lista
    driver = None
    for d in drivers:
        if d in available_drivers:
            driver = d
            break

    if not driver:
        # Fallback para qualquer driver SQL Server disponível
        driver = available_drivers[0] if available_drivers else "ODBC Driver 18 for SQL Server"

    # Separa host e instância (formato: servidor\instancia)
    if '\\' in host:
        server, instance = host.split('\\', 1)
        return f"DRIVER={{{driver}}};SERVER={server}\\{instance};DATABASE={database};UID={user};PWD={password};TrustServerCertificate=yes"
    else:
        return f"DRIVER={{{driver}}};SERVER={host};DATABASE={database};UID={user};PWD={password};TrustServerCertificate=yes"


def test_connection(host: str, database: str, user: str, password: str) -> Tuple[bool, str]:
    """Testa conexão com o SQL Server."""
    try:
        conn_str = get_connection_string(host, database, user, password)
        conn = pyodbc.connect(conn_str, timeout=10)
        conn.close()
        return True, "Conexão estabelecida com sucesso!"
    except Exception as e:
        return False, f"Erro ao conectar: {str(e)}"


def check_company_exists(conn: pyodbc.Connection, code5: str) -> bool:
    """Verifica se a tabela da empresa existe no banco."""
    try:
        cursor = conn.cursor()
        query = """
        SELECT TOP 1 1 AS ok
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id = o.schema_id
        WHERE s.name = 'WFiscal'
          AND o.name = ?
          AND o.type IN ('U','V')
        """
        cursor.execute(query, f"M{code5}")
        result = cursor.fetchone()
        return result is not None
    except Exception:
        return False


def extract_bi_data(
    host: str,
    database: str,
    user: str,
    password: str,
    company_code: str,
    start_date: datetime,
    end_date: datetime,
    municipio_id: Optional[int] = None
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], str]:
    """
    Extrai dados de BI do Alterdata para uma empresa específica.

    Args:
        host: Servidor SQL (pode incluir instância: servidor\\instancia)
        database: Nome do banco de dados
        user: Usuário SQL
        password: Senha SQL
        company_code: Código da empresa (será padronizado para 5 dígitos)
        start_date: Data inicial
        end_date: Data final (exclusiva)
        municipio_id: ID do município (opcional)

    Returns:
        Tupla (df_entrada, df_saida, mensagem)
    """
    try:
        # Padroniza código para 5 dígitos
        code5 = str(company_code).zfill(5)

        # Conecta ao banco
        conn_str = get_connection_string(host, database, user, password)
        conn = pyodbc.connect(conn_str, timeout=30)

        # Verifica se empresa existe
        if not check_company_exists(conn, code5):
            conn.close()
            return None, None, f"Empresa {code5} não encontrada no banco de dados (tabela WFiscal.M{code5} não existe)"

        # Prepara parâmetros
        municipio_param = municipio_id if municipio_id is not None else None

        # Extrai dados de SAÍDA
        query_saida = QUERY_SAIDA.replace("{code5}", code5)
        df_saida = pd.read_sql(query_saida, conn, params=[municipio_param, start_date, end_date])

        # Extrai dados de ENTRADA
        query_entrada = QUERY_ENTRADA.replace("{code5}", code5)
        df_entrada = pd.read_sql(query_entrada, conn, params=[municipio_param, start_date, end_date])

        conn.close()

        msg = f"Extração concluída: {len(df_entrada)} registros de Entrada, {len(df_saida)} registros de Saída"
        return df_entrada, df_saida, msg

    except Exception as e:
        return None, None, f"Erro ao extrair dados: {str(e)}"


def extract_bi_data_from_env(
    company_code: str,
    start_date: datetime,
    end_date: datetime,
    municipio_id: Optional[int] = None
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], str]:
    """
    Extrai dados de BI usando credenciais do arquivo .env.

    Args:
        company_code: Código da empresa (será padronizado para 5 dígitos)
        start_date: Data inicial
        end_date: Data final (exclusiva)
        municipio_id: ID do município (opcional)

    Returns:
        Tupla (df_entrada, df_saida, mensagem)
    """
    # Obtém credenciais do .env
    host, database, user, password = get_db_credentials()

    # Valida se credenciais foram carregadas
    if not all([host, database, user, password]):
        return None, None, "Erro: Credenciais não encontradas no arquivo Alterdata_BI/.env"

    # Chama função original com credenciais
    return extract_bi_data(
        host=host,
        database=database,
        user=user,
        password=password,
        company_code=company_code,
        start_date=start_date,
        end_date=end_date,
        municipio_id=municipio_id
    )


def test_connection_from_env() -> Tuple[bool, str]:
    """
    Testa conexão com SQL Server usando credenciais do .env.

    Returns:
        Tupla (sucesso, mensagem)
    """
    host, database, user, password = get_db_credentials()

    if not all([host, database, user, password]):
        return False, "Credenciais não encontradas no arquivo Alterdata_BI/.env"

    return test_connection(host, database, user, password)


def generate_excel_file(
    df_entrada: pd.DataFrame,
    df_saida: pd.DataFrame,
    company_code: str,
    start_date: datetime,
    end_date: datetime,
    output_dir: str = "temp_bi"
) -> Tuple[Optional[str], str]:
    """
    Gera arquivo Excel com as abas Entrada e Saída.

    Args:
        df_entrada: DataFrame com dados de entrada
        df_saida: DataFrame com dados de saída
        company_code: Código da empresa
        start_date: Data inicial
        end_date: Data final
        output_dir: Diretório de saída

    Returns:
        Tupla (caminho_arquivo, mensagem)
    """
    try:
        # Cria diretório se não existe
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Padroniza código
        code5 = str(company_code).zfill(5)

        # Nome do arquivo
        today = datetime.now()
        filename = f"{code5}_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}_{today.strftime('%d-%m-%Y')}.xlsx"
        filepath = Path(output_dir) / filename

        # Gera Excel
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Aba Entrada
            if df_entrada.empty:
                pd.DataFrame([["(sem registros no período)"]]).to_excel(writer, sheet_name='Entrada', index=False, header=False)
            else:
                df_entrada.to_excel(writer, sheet_name='Entrada', index=False)

            # Aba Saída
            if df_saida.empty:
                pd.DataFrame([["(sem registros no período)"]]).to_excel(writer, sheet_name='Saída', index=False, header=False)
            else:
                df_saida.to_excel(writer, sheet_name='Saída', index=False)

        return str(filepath), f"Arquivo gerado com sucesso: {filename}"

    except Exception as e:
        return None, f"Erro ao gerar Excel: {str(e)}"
