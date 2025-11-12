// queries.js
// Observações importantes:
// - Deixe "FROM WFiscal.M02122 M" literalmente; o index.js substitui M02122 -> M00xxx por empresa.
// - Parâmetros usados: @DtInicial, @DtFinal (exclusiva), @IdMunicipio.
// - Substituí SYSTEM.ALT_ROUNDREAL por ROUND e ALT_STRZERO por RIGHT(REPLICATE(...)) para evitar GRANT EXECUTE.
// - Ordem das colunas preservada e incluída a coluna [Lanc. Cont. Vl. ICMS] logo após [Lanc. Cont. Vl. Contábil].

const QUERY_SAIDA = `
SELECT DISTINCT
/*  1 */ CAST(CASE WHEN M.StCancelada = 'S' THEN 'Sim' ELSE 'Não' END AS VARCHAR(3)) AS [Cancelada],
/*  2 */ M.dtEscrituracao                                   AS [Dt. Escrituração],
/*  3 */ M.DtEmissao                                        AS [Data Emissão],
/*  4 */ M.IdCodFiscal                                      AS [CFOP],
/*  5 */ CAST(CASE
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
              ELSE '' END AS VARCHAR(30))                   AS [Tipo CFOP],
/*  6 */ M.NmNumero                                         AS [Número],
/*  7 */ F.NmNome                                           AS [Nome Forn/Cliente],
/*  8 */ M.VlContabil                                       AS [Valor Contábil],
/*  9 */ ROUND(COALESCE(M.VlICMSValor,0), 2)                AS [Vl. ICMS],
/* 10 */ M.VlValorST                                        AS [Vl. ST],
/* 11 */ M.VlIPIValor                                       AS [Vl. IPI],
/* 12 */ M.IdTipoOperacao                                   AS [Cód. Oper. Contábil],
/* 13 */ M.IdLancContabil                                   AS [Lanc. Cont. Vl. Contábil],
/* 14 */ M.IdLancIcms                                       AS [Lanc. Cont. Vl. ICMS],
/* 15 */ M.IdLancIcmsST                                     AS [Lanc. Cont. Vl. Subst. Trib.],
/* 16 */ M.IdLancIpi                                        AS [Lanc. Cont. Vl. IPI],
/* 17 */ CAST(CASE
              WHEN COALESCE(CASE WHEN ZOP.Exportado = CAST(1 AS bit) THEN 'S' ELSE M.StExportado END,'N')='S'
              THEN 'Sim' ELSE 'Não' END AS VARCHAR(3))      AS [Exportado],
/* 18 */ M.VlBaseST                                         AS [Base ST],
/* 19 */ COALESCE(M.Total_Pis_Unidade_Medida,0)
       + COALESCE(M.Total_Pis_Cumulativo,0)
       + COALESCE(M.Total_Pis_Nao_Cumulativo,0)             AS [Total PIS],
/* 20 */ COALESCE(M.Total_Cofins_Unidade_Medida,0)
       + COALESCE(M.Total_Cofins_Cumulativo,0)
       + COALESCE(M.Total_Cofins_Nao_Cumulativo,0)          AS [Total CONFINS],
/* 21 */ M.VlIPIBase                                        AS [Vl. Base IPI],
/* 22 */ M.VlIPIAliquota                                    AS [% IPI],
/* 23 */ M.VlIPINaoAproveitado                              AS [IPI Não Aproveitado],
/* 24 */ M.VlICMSBase                                       AS [Vl. Base ICMS],
/* 25 */ M.VlICMSAliquota                                   AS [%ICMS],
/* 26 */ M.CSTICMS                                          AS [CST ICMS],
/* 27 */ M.informacao_complementar                          AS [Informações Complementares],
/* 28 */ CONVERT(DATETIME, M.data_importacao)               AS [Data da Importação],
/* 29 */ M.nome_usuario_importacao                          AS [Usuário Importador],
/* 30 */ F.CdCgc                                            AS [CNPJ/CPF forn/Cliente],
/* 31 */ M.IdModDocFiscal                                   AS [Mod.],
/* 32 */ M.chave_acesso_nota_eletronica                     AS [Chave de Acesso NFe/CF SAT]
FROM WFiscal.M02122 M
LEFT JOIN WFISCAL.movimento_reducao_z Z
       ON Z.Data    = M.DtEscrituracao
      AND Z.Ecf_Id  = M.CodECF
LEFT JOIN WFISCAL.movimento_reducao_z_por_operacao ZOP
       ON ZOP.Movimento_Reducao_Z_Id = Z.Id
      AND ZOP.cfop                   = M.IdCodFiscal
      AND ZOP.aliquota_icms          = M.VlICMSAliquota
      AND RIGHT(REPLICATE('0',3) + CAST(ZOP.cst_icms AS VARCHAR(3)), 3)
          = RIGHT(REPLICATE('0',3) + CAST(M.CSTICMS   AS VARCHAR(3)), 3)
LEFT JOIN WFiscal.CadFisM CFOP ON M.IdCodFiscal = CFOP.IdCodigo
LEFT JOIN wfiscal.FORNEC F     ON M.IdCodForCli = F.CdFornecedor
LEFT JOIN wphd.MunicipiosIBGE MUN
       ON (MUN.IdMunicipio = F.IdMunicipio AND M.TpEmissaoNF <> 'S')
       OR (MUN.IdMunicipio = @IdMunicipio   AND M.TpEmissaoNF  = 'S')
LEFT JOIN wfiscal.arquivos_xml_danfe X ON M.chave_acesso_nota_eletronica = X.id
LEFT JOIN WFiscal.MODDOC MD            ON M.IdModDocFiscal = MD.CdCodigo
WHERE M.dtEscrituracao >= @DtInicial
  AND M.dtEscrituracao <  @DtFinal
  AND M.StTipo = 'S'
  AND ISNULL(NULLIF(LTRIM(RTRIM(M.StCancelada)), ''), 'N') = 'N';
`;

const QUERY_ENTRADA = `
SELECT DISTINCT
/*  1 */ CAST(CASE WHEN M.StCancelada = 'S' THEN 'Sim' ELSE 'Não' END AS VARCHAR(3)) AS [Cancelada],
/*  2 */ M.dtEscrituracao                                   AS [Dt. Escrituração],
/*  3 */ M.DtEmissao                                        AS [Data Emissão],
/*  4 */ M.IdCodFiscal                                      AS [CFOP],
/*  5 */ CAST(CASE
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
              ELSE '' END AS VARCHAR(30))                   AS [Tipo CFOP],
/*  6 */ M.NmNumero                                         AS [Número],
/*  7 */ F.NmNome                                           AS [Nome Forn/Cliente],
/*  8 */ M.VlContabil                                       AS [Valor Contábil],
/*  9 */ ROUND(COALESCE(M.VlICMSValor,0), 2)                AS [Vl. ICMS],
/* 10 */ M.VlValorST                                        AS [Vl. ST],
/* 11 */ M.VlIPIValor                                       AS [Vl. IPI],
/* 12 */ M.IdTipoOperacao                                   AS [Cód. Oper. Contábil],
/* 13 */ M.IdLancContabil                                   AS [Lanc. Cont. Vl. Contábil],
/* 14 */ M.IdLancIcms                                       AS [Lanc. Cont. Vl. ICMS],
/* 15 */ M.IdLancIcmsST                                     AS [Lanc. Cont. Vl. Subst. Trib.],
/* 16 */ M.IdLancIpi                                        AS [Lanc. Cont. Vl. IPI],
/* 17 */ CAST(CASE
              WHEN COALESCE(CASE WHEN ZOP.Exportado = CAST(1 AS bit) THEN 'S' ELSE M.StExportado END,'N')='S'
              THEN 'Sim' ELSE 'Não' END AS VARCHAR(3))      AS [Exportado],
/* 18 */ M.VlBaseST                                         AS [Base ST],
/* 19 */ COALESCE(M.Total_Pis_Unidade_Medida,0)
       + COALESCE(M.Total_Pis_Cumulativo,0)
       + COALESCE(M.Total_Pis_Nao_Cumulativo,0)             AS [Total PIS],
/* 20 */ COALESCE(M.Total_Cofins_Unidade_Medida,0)
       + COALESCE(M.Total_Cofins_Cumulativo,0)
       + COALESCE(M.Total_Cofins_Nao_Cumulativo,0)          AS [Total CONFINS],
/* 21 */ M.VlIPIBase                                        AS [Vl. Base IPI],
/* 22 */ M.VlIPIAliquota                                    AS [% IPI],
/* 23 */ M.VlIPINaoAproveitado                              AS [IPI Não Aproveitado],
/* 24 */ M.VlICMSBase                                       AS [Vl. Base ICMS],
/* 25 */ M.VlICMSAliquota                                   AS [%ICMS],
/* 26 */ M.CSTICMS                                          AS [CST ICMS],
/* 27 */ M.informacao_complementar                          AS [Informações Complementares],
/* 28 */ CONVERT(DATETIME, M.data_importacao)               AS [Data da Importação],
/* 29 */ M.nome_usuario_importacao                          AS [Usuário Importador],
/* 30 */ F.CdCgc                                            AS [CNPJ/CPF forn/Cliente],
/* 31 */ M.IdModDocFiscal                                   AS [Mod.],
/* 32 */ M.chave_acesso_nota_eletronica                     AS [Chave de Acesso NFe/CF SAT]
FROM WFiscal.M02122 M
LEFT JOIN WFISCAL.movimento_reducao_z Z
       ON Z.Data    = M.DtEscrituracao
      AND Z.Ecf_Id  = M.CodECF
LEFT JOIN WFISCAL.movimento_reducao_z_por_operacao ZOP
       ON ZOP.Movimento_Reducao_Z_Id = Z.Id
      AND ZOP.cfop                   = M.IdCodFiscal
      AND ZOP.aliquota_icms          = M.VlICMSAliquota
      AND RIGHT(REPLICATE('0',3) + CAST(ZOP.cst_icms AS VARCHAR(3)), 3)
          = RIGHT(REPLICATE('0',3) + CAST(M.CSTICMS   AS VARCHAR(3)), 3)
LEFT JOIN WFiscal.CadFisM CFOP ON M.IdCodFiscal = CFOP.IdCodigo
LEFT JOIN wfiscal.FORNEC F     ON M.IdCodForCli = F.CdFornecedor
LEFT JOIN wphd.MunicipiosIBGE MUN
       ON (MUN.IdMunicipio = F.IdMunicipio AND M.TpEmissaoNF <> 'S')
       OR (MUN.IdMunicipio = @IdMunicipio   AND M.TpEmissaoNF  = 'S')
LEFT JOIN wfiscal.arquivos_xml_danfe X ON M.chave_acesso_nota_eletronica = X.id
LEFT JOIN WFiscal.MODDOC MD            ON M.IdModDocFiscal = MD.CdCodigo
WHERE M.dtEscrituracao >= @DtInicial
  AND M.dtEscrituracao <  @DtFinal
  AND M.StTipo = 'E'
  AND ISNULL(NULLIF(LTRIM(RTRIM(M.StCancelada)), ''), 'N') = 'N';
`;

module.exports = { QUERY_SAIDA, QUERY_ENTRADA };