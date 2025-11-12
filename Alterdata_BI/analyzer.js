// analyzer.js
// - Cód. Oper. Contábil = 1 (Entrada/Saída)
// - Notas duplicadas (Número, CFOP, Valor Contábil, CST ICMS)
// - Lançamentos contábeis por CFOP (colunas D, M, N, O, P) com base no JSON remoto

const ExcelJS = require('exceljs');
const path = require('path');
const https = require('https');

// ---------- Helpers ----------
function normalizeHeader(s) {
  if (s == null) return '';
  return String(s)
    .trim()
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[.\s]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
function isRowEmpty(row) {
  if (!row) return true;
  for (let c = 1; c <= row.cellCount; c++) {
    const v = row.getCell(c).value;
    if (v !== null && v !== undefined && String(v).trim() !== '') return false;
  }
  return true;
}
function numberish(v) {
  if (v == null) return null;
  const s = String(v).trim().replace(/\./g, '').replace(',', '.');
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}
function httpGetJson(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      if (res.statusCode !== 200) {
        reject(new Error(`GET ${url} -> ${res.statusCode}`));
        res.resume();
        return;
      }
      let data = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(e); }
      });
    }).on('error', reject);
  });
}
function getSheetIfExists(wb, name) {
  const ws = wb.getWorksheet(name);
  return ws || null;
}

// ---------- (1) Cód. Oper. Contábil = 1 ----------
function findCodOperColumn(ws) {
  const headerRow = ws?.getRow(1);
  if (!headerRow || headerRow.cellCount === 0) return null;
  const target = 'cod oper contabil';
  for (let c = 1; c <= headerRow.cellCount; c++) {
    const raw = headerRow.getCell(c).value;
    if (normalizeHeader(raw) === target) return c;
  }
  return null;
}
function cellIsOne(val) {
  if (val == null) return false;
  const s = String(val).trim();
  const num = Number(s.replace(',', '.'));
  if (!Number.isNaN(num) && num === 1) return true;
  return s === '1' || s === '01' || s === '1.0';
}
function sheetAllOnes(ws, logger) {
  if (!ws) return true;
  const rowCount = ws.rowCount || 0;
  if (rowCount <= 1) return true;

  const r2 = ws.getRow(2);
  if (r2 && !isRowEmpty(r2)) {
    const joined = Array.from({ length: r2.cellCount || 1 }, (_, i) => r2.getCell(i + 1).value)
      .map(v => (v == null ? '' : String(v))).join(' ').toLowerCase();
    if (/\(sem registros no periodo\)|\(sem registros no período\)/i.test(joined)) return true;
  }

  const colIdx = findCodOperColumn(ws);
  if (colIdx == null) {
    logger?.write?.(`(analyzer) Cabeçalho "Cód. Oper. Contábil" não encontrado em "${ws?.name}". Ignorando esta guia (não reprova).`);
    return true;
  }

  for (let r = 2; r <= rowCount; r++) {
    const row = ws.getRow(r);
    if (isRowEmpty(row)) continue;
    const raw = row.getCell(colIdx)?.value;
    if (!cellIsOne(raw)) return false;
  }
  return true;
}
async function analyzeCodOperContabil({ resultados, logger }) {
  const details = [];
  const failing = [];
  for (const r of (resultados || [])) {
    const file = r.outFile;
    const code5 = r.code5;
    try {
      const wb = new ExcelJS.Workbook();
      await wb.xlsx.readFile(file);
      const wsEntrada = getSheetIfExists(wb, 'Entrada');
      const wsSaida   = getSheetIfExists(wb, 'Saída');

      const entradaOk = sheetAllOnes(wsEntrada, logger);
      const saidaOk   = sheetAllOnes(wsSaida, logger);

      details.push({ code5, entradaOk, saidaOk, file });
      if (!(entradaOk && saidaOk)) failing.push(code5);
    } catch (err) {
      logger?.write?.(`(analyzer) Falha ao analisar ${code5} (${path.basename(file)}): ${err?.message || err}`);
      details.push({ code5, entradaOk: false, saidaOk: false, file, error: String(err?.message || err) });
      failing.push(code5);
    }
  }
  return { failingCodes: failing, details };
}

// ---------- (2) Notas duplicadas ----------
function findDupColumns(ws) {
  const header = ws?.getRow(1);
  if (!header || header.cellCount === 0) return { numero: 6, cfop: 4, valor: 8, cst: 26 }; // F,D,H,Z
  const indices = { numero: null, cfop: null, valor: null, cst: null };
  for (let c = 1; c <= header.cellCount; c++) {
    const h = normalizeHeader(header.getCell(c).value);
    if (!indices.numero && (h === 'numero' || h === 'numero nf' || h === 'numero nfe')) indices.numero = c;
    if (!indices.cfop   && h === 'cfop') indices.cfop = c;
    if (!indices.valor  && (h === 'valor contabil' || h === 'vl contabil' || h === 'valor contab')) indices.valor = c;
    if (!indices.cst    && (h === 'cst icms' || h === 'cst do icms')) indices.cst = c;
  }
  return {
    numero: indices.numero || 6,  // F
    cfop:   indices.cfop   || 4,  // D
    valor:  indices.valor  || 8,  // H
    cst:    indices.cst    || 26, // Z
  };
}
function sheetHasDuplicates(ws) {
  if (!ws) return false;
  const rowCount = ws.rowCount || 0;
  if (rowCount <= 1) return false;

  const r2 = ws.getRow(2);
  if (r2 && !isRowEmpty(r2)) {
    const joined = Array.from({ length: r2.cellCount || 1 }, (_, i) => r2.getCell(i + 1).value)
      .map(v => (v == null ? '' : String(v))).join(' ').toLowerCase();
    if (/\(sem registros no periodo\)|\(sem registros no período\)/i.test(joined)) return false;
  }

  const { numero, cfop, valor, cst } = findDupColumns(ws);
  const seen = new Map();

  for (let r = 2; r <= rowCount; r++) {
    const row = ws.getRow(r);
    if (isRowEmpty(row)) continue;

    const vNumero = String(row.getCell(numero)?.value ?? '').trim();
    const vCfop   = String(row.getCell(cfop)?.value ?? '').trim();
    const vValor  = numberish(row.getCell(valor)?.value);
    const vCst    = String(row.getCell(cst)?.value ?? '').trim();

    const key = `${vNumero}|${vCfop}|${vValor ?? 'null'}|${vCst}`;
    if (seen.has(key)) return true;
    seen.set(key, true);
  }
  return false;
}
async function analyzeNotasDuplicadas({ resultados, logger }) {
  const failing = [];
  const details = [];

  for (const r of (resultados || [])) {
    const file = r.outFile;
    const code5 = r.code5;
    try {
      const wb = new ExcelJS.Workbook();
      await wb.xlsx.readFile(file);

      const wsEntrada = getSheetIfExists(wb, 'Entrada');
      const wsSaida   = getSheetIfExists(wb, 'Saída');

      const dupEntrada = sheetHasDuplicates(wsEntrada);
      const dupSaida   = sheetHasDuplicates(wsSaida);

      details.push({ code5, dupEntrada, dupSaida, file });
      if (dupEntrada || dupSaida) failing.push(code5);
    } catch (err) {
      logger?.write?.(`(analyzer) Falha ao analisar duplicidade ${code5} (${path.basename(file)}): ${err?.message || err}`);
    }
  }
  return { failingCodes: failing, details };
}

// ---------- (3) Lançamentos contábeis por CFOP ----------
const CFOP_JSON_URL = 'https://raw.githubusercontent.com/Petrakis20/Conferencia-Livro-Razao/main/cfop_base.json';

function findColumnsCfopCodes(ws) {
  // Preferência por cabeçalho; fallback para letras fixas: D(4), M(13), N(14), O(15), P(16)
  const header = ws?.getRow(1);
  const cols = { cfop: 4, contabil: 13, icms: 14, icms_subst: 15, ipi: 16 }; // Fallback

  if (!header || header.cellCount === 0) return cols;

  for (let c = 1; c <= header.cellCount; c++) {
    const h = normalizeHeader(header.getCell(c).value);
    if (h === 'cfop') cols.cfop = c;
    if (h === 'lanc cont vl contabil' || h === 'lanc cont vl contab' || h === 'lancamento cont vl contabil') cols.contabil = c;
    if (h === 'lanc cont vl icms'     || h === 'lancamento cont vl icms') cols.icms = c;
    if (h === 'lanc cont vl subst trib' || h === 'lancamento cont vl subst trib' || h === 'lanc cont vl sub trib') cols.icms_subst = c;
    if (h === 'lanc cont vl ipi'      || h === 'lancamento cont vl ipi') cols.ipi = c;
  }
  return cols;
}

function valueStr(cellVal) {
  if (cellVal == null) return '';
  return String(cellVal).trim();
}

function compareCfopRow(cfopMap, cfopCode, vContabil, vIcms, vIcmsSubst, vIpi) {
  const expected = cfopMap[String(cfopCode).trim()];
  if (!expected) return true; // CFOP não mapeado => não reprova

  // expected.icms_subst pode ser null (aceita vazio)
  const okContabil = expected.contabil == null ? vContabil === '' : String(expected.contabil) === vContabil;
  const okIcms     = expected.icms     == null ? vIcms     === '' : String(expected.icms)     === vIcms;
  const okIpi      = expected.ipi      == null ? vIpi      === '' : String(expected.ipi)      === vIpi;

  let okSubst;
  if (expected.icms_subst == null) {
    // aceita vazio ou zero
    okSubst = (vIcmsSubst === '' || vIcmsSubst === '0' || vIcmsSubst === '00');
  } else {
    okSubst = String(expected.icms_subst) === vIcmsSubst;
  }

  return okContabil && okIcms && okSubst && okIpi;
}

function sheetCfopCodesOk(ws, cfopMap) {
  if (!ws) return true;
  const rowCount = ws.rowCount || 0;
  if (rowCount <= 1) return true;

  const r2 = ws.getRow(2);
  if (r2 && !isRowEmpty(r2)) {
    const joined = Array.from({ length: r2.cellCount || 1 }, (_, i) => r2.getCell(i + 1).value)
      .map(v => (v == null ? '' : String(v))).join(' ').toLowerCase();
    if (/\(sem registros no periodo\)|\(sem registros no período\)/i.test(joined)) return true;
  }

  const { cfop, contabil, icms, icms_subst, ipi } = findColumnsCfopCodes(ws);

  for (let r = 2; r <= rowCount; r++) {
    const row = ws.getRow(r);
    if (isRowEmpty(row)) continue;

    const vCfop      = valueStr(row.getCell(cfop)?.value);
    const vContabil  = valueStr(row.getCell(contabil)?.value);
    const vIcms      = valueStr(row.getCell(icms)?.value);
    const vIcmsSubst = valueStr(row.getCell(icms_subst)?.value);
    const vIpi       = valueStr(row.getCell(ipi)?.value);

    if (!vCfop) continue; // sem CFOP não avalia

    const ok = compareCfopRow(cfopMap, vCfop, vContabil, vIcms, vIcmsSubst, vIpi);
    if (!ok) return false;
  }
  return true;
}

async function analyzeLancamentosPorCFOP({ resultados, logger }) {
  // 1) Baixa o JSON (sempre mais recente)
  let cfopMap = {};
  try {
    cfopMap = await httpGetJson(CFOP_JSON_URL);
    if (!cfopMap || typeof cfopMap !== 'object') throw new Error('JSON CFOP inválido');
  } catch (err) {
    logger?.write?.(`(analyzer) Falha ao obter cfop_base.json: ${err?.message || err}`);
    // Conservador: não reprova ninguém se não conseguiu baixar o mapa
    return { failingCodes: [], details: [], warning: 'Não foi possível obter cfop_base.json' };
  }

  const failing = [];
  const details = [];

  for (const r of (resultados || [])) {
    const file = r.outFile;
    const code5 = r.code5;

    try {
      const wb = new ExcelJS.Workbook();
      await wb.xlsx.readFile(file);

      const wsEntrada = getSheetIfExists(wb, 'Entrada');
      const wsSaida   = getSheetIfExists(wb, 'Saída');

      const entradaOk = sheetCfopCodesOk(wsEntrada, cfopMap);
      const saidaOk   = sheetCfopCodesOk(wsSaida, cfopMap);

      details.push({ code5, entradaOk, saidaOk, file });

      if (!(entradaOk && saidaOk)) failing.push(code5);
    } catch (err) {
      // Se não conseguiu ler o arquivo, marca como falha para não passar batido
      details.push({ code5, entradaOk: false, saidaOk: false, file, error: String(err?.message || err) });
      failing.push(code5);
      logger?.write?.(`(analyzer) Falha ao analisar CFOP ${code5} (${path.basename(file)}): ${err?.message || err}`);
    }
  }

  return { failingCodes: failing, details };
}

module.exports = {
  analyzeCodOperContabil,
  analyzeNotasDuplicadas,
  analyzeLancamentosPorCFOP
};