// index.js
// -------------------------------------------------------------------------------------
// Exportador BI + Agendamento por dia + Execução de PowerShell no pós-processamento
// -------------------------------------------------------------------------------------
const fs = require('fs');
const path = require('path');
const ExcelJS = require('exceljs');
const sql = require('mssql');
const yargs = require('yargs');
const { hideBin } = require('yargs/helpers');
const { spawn } = require('child_process');
const { sendSummaryEmail } = require('./mailer');
const { analyzeCodOperContabil, analyzeNotasDuplicadas, analyzeLancamentosPorCFOP } = require('./analyzer.js');
require('dotenv').config();

// Ajuste para CommonJS: certifique-se de que queries.js exporta via module.exports
// { QUERY_SAIDA, QUERY_ENTRADA }
const { QUERY_SAIDA, QUERY_ENTRADA } = require('./queries.js');

// --- Defaults ---
const DEFAULT_LOG_DIR     = process.env.LOG_DIR || 'C:\\scripts\\log_BI_Contabil';
const DEFAULT_OUT_DIR     = process.env.BI_OUT  || 'C:\\Relatorios';
const DEFAULT_CONFIG_PATH = process.env.BI_CFG  || 'C:\\script\\Robo_BI_Contabil\\params.txt';

// ---------------- CLI ----------------
const argv = yargs(hideBin(process.argv))
  .option('cfg',       { type: 'string', describe: 'Caminho do arquivo de parâmetros (txt)', default: DEFAULT_CONFIG_PATH })
  .option('start',     { alias: 's', type: 'string', describe: 'Data inicial (YYYY-MM-DD)' })
  .option('end',       { alias: 'e', type: 'string', describe: 'Data final exclusiva (YYYY-MM-DD)' })
  .option('municipio', { alias: 'm', type: 'string', describe: 'Id do município (ou "null")' })
  .option('empresas',  { alias: 'c', type: 'string', describe: 'Códigos de empresa separados por ; (ex.: "552;1024")' })
  .option('out',       { alias: 'o', type: 'string', describe: 'Pasta de saída dos .xlsx' })
  .option('day',       { type: 'number', describe: 'Força o dia do mês (apenas para teste)' })
  .help().argv;

// ---------------- Utils ----------------
function ensureDirSync(dir) {
  if (!dir) return;
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}
function zeroPad5(v) {
  if (v == null) return '';
  const digits = String(v).replace(/[^\d]/g, '');
  if (!digits) return '';
  return digits.padStart(5, '0');
}
function formatDate(dt, sep='-') {
  const y = dt.getFullYear();
  const m = String(dt.getMonth()+1).padStart(2,'0');
  const d = String(dt.getDate()).padStart(2,'0');
  return `${y}${sep}${m}${sep}${d}`;
}
function formatMs(ms) {
  const s  = Math.floor(ms / 1000);
  const mm = Math.floor(s / 60);
  const hh = Math.floor(mm / 60);
  const remS = s % 60;
  const remM = mm % 60;
  let out = '';
  if (hh) out += `${hh}h `;
  if (remM) out += `${remM}m `;
  out += `${remS}s`;
  return out.trim();
}
function parseISODate(s) {
  if (!s) return null;
  const m = String(s).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return null;
  const dt = new Date(`${m[1]}-${m[2]}-${m[3]}T00:00:00`);
  if (Number.isNaN(dt.getTime())) return null;
  return dt;
}
function getDayInTimezone(tz = 'America/Sao_Paulo', forcedDay) {
  if (typeof forcedDay === 'number' && forcedDay >= 1 && forcedDay <= 31) return forcedDay;
  const now = new Date();
  const sp = new Date(now.toLocaleString('en-US', { timeZone: tz }));
  return sp.getDate();
}
function splitCliArgs(argLine) {
  if (!argLine) return [];
  const re = /"([^"]*)"|'([^']*)'|([^\s]+)/g;
  const out = [];
  let m;
  while ((m = re.exec(argLine))) out.push(m[1] || m[2] || m[3]);
  return out;
}

// ---------------- Logger ----------------
class Logger {
  constructor(dir) {
    ensureDirSync(dir);
    const now = new Date();
    const file = `bi_export_${formatDate(now,'-')}_${String(now.getHours()).padStart(2,'0')}-${String(now.getMinutes()).padStart(2,'0')}-${String(now.getSeconds()).padStart(2,'0')}.log`;
    this.logPath = path.join(dir, file);
    this.stream = fs.createWriteStream(this.logPath, { flags: 'a', encoding: 'utf8' });
  }
  write(msg) {
    const ts = new Date().toISOString().replace('T',' ').replace('Z','');
    this.stream.write(`${ts} ${msg}\n`);
    console.log(msg);
  }
  close() { try { this.stream.end(); } catch {} }
}

// ---------------- SQL Server ----------------
function parseHostInstance(hostEnv) {
  if (!hostEnv) return { host: '', instance: null };
  if (hostEnv.includes('\\')) {
    const [host, instance] = hostEnv.split('\\');
    return { host, instance };
  }
  return { host: hostEnv, instance: null };
}

async function getPool() {
  const { host, instance } = parseHostInstance(process.env.DB_HOST);
  const config = {
    user: process.env.DB_USER,
    password: process.env.DB_PASS,
    server: host || process.env.DB_HOST,
    database: process.env.DB_NAME,
    options: {
      encrypt: String(process.env.DB_ENCRYPT).toLowerCase() === 'true',
      trustServerCertificate: String(process.env.DB_TRUST_CERT).toLowerCase() !== 'false',
      ...(instance ? { instanceName: instance } : {})
    },
    pool: { max: 5, min: 0, idleTimeoutMillis: 30000 }
  };
  const pool = new sql.ConnectionPool(config);
  await pool.connect();
  return pool;
}

async function checkCompanyTableExists(pool, code5) {
  const fullName = `WFiscal.M${code5}`;
  const q = `
    DECLARE @obj SYSNAME = @full;
    SELECT TOP 1 1 AS ok
    FROM sys.objects o
    JOIN sys.schemas s ON s.schema_id = o.schema_id
    WHERE s.name = PARSENAME(@obj, 2)
      AND o.name = PARSENAME(@obj, 1)
      AND o.type IN ('U','V');
  `;
  const rs = await pool.request().input('full', sql.NVarChar(261), fullName).query(q);
  return rs && rs.recordset && rs.recordset.length > 0;
}

// ---------------- Query helpers ----------------
function injectCompanyTable(query, code5) {
  return query.replace(/WFiscal\.M\d{5}/g, `WFiscal.M${code5}`);
}
function buildRequest(pool, { start, end, municipio }) {
  const r = pool.request();
  if (start) r.input('DtInicial', sql.Date, start);
  if (end)   r.input('DtFinal',   sql.Date, end);
  if (municipio === null) {
    r.input('IdMunicipio', sql.Int, null);
  } else if (municipio === undefined || municipio === '') {
    r.input('IdMunicipio', sql.Int, null);
  } else {
    const asInt = Number(municipio);
    r.input('IdMunicipio', sql.Int, Number.isFinite(asInt) ? asInt : null);
  }
  return r;
}

async function queryToWorksheet(pool, ws, sqlText, params, logger) {
  const req = buildRequest(pool, params);
  const rs  = await req.query(sqlText);
  const rows = rs.recordset || [];

  if (rows.length === 0) {
    ws.addRow(['(sem registros no período)']);
    return { count: 0 };
  }

  const headers = Object.keys(rows[0]);
  ws.addRow(headers);
  ws.getRow(1).font = { bold: true };

  for (const row of rows) {
    const vals = headers.map(h => row[h]);
    ws.addRow(vals);
  }
  ws.columns.forEach((col) => {
    let max = 10;
    col.eachCell({ includeEmpty: true }, (cell) => {
      const v = cell.value == null ? '' : String(cell.value);
      if (v.length > max) max = v.length;
    });
    col.width = Math.min(60, Math.max(10, max + 2));
  });

  logger && logger.write(`  -> ${rows.length} linha(s)`);
  return { count: rows.length };
}

async function exportCompany(pool, code5, { start, end, municipio, outDir }, logger) {
  const todaySP = new Date(new Date().toLocaleString('en-US', { timeZone: 'America/Sao_Paulo' }));
  const fileName = `${code5}_${start || ''}_${end || ''}_${String(todaySP.getDate()).padStart(2,'0')}-${String(todaySP.getMonth()+1).padStart(2,'0')}-${todaySP.getFullYear()}.xlsx`;
  const outFile = path.join(outDir || DEFAULT_OUT_DIR, fileName);

  const wb = new ExcelJS.Workbook();

  // Saída
  logger.write(`Saída (WFiscal.M${code5})...`);
  const wsOut = wb.addWorksheet('Saída');
  const qOut  = injectCompanyTable(QUERY_SAIDA, code5);
  const t1 = Date.now();
  await queryToWorksheet(pool, wsOut, qOut, { start, end, municipio }, logger);
  const t2 = Date.now();

  // Entrada
  logger.write(`Entrada (WFiscal.M${code5})...`);
  const wsIn = wb.addWorksheet('Entrada');
  const qIn  = injectCompanyTable(QUERY_ENTRADA, code5);
  const t3 = Date.now();
  await queryToWorksheet(pool, wsIn, qIn, { start, end, municipio }, logger);
  const t4 = Date.now();

  ensureDirSync(outDir || DEFAULT_OUT_DIR);
  await wb.xlsx.writeFile(outFile);

  return {
    outFile,
    tempoSaida:   (t2 - t1),
    tempoEntrada: (t4 - t3),
    tempoTotalEmpresa: (t4 - t1)
  };
}

// ---------------- params.txt parser (com blocos por dia) ----------------
function loadConfigFile(filePath) {
  const res = { start: undefined, end: undefined, municipio: undefined, out: undefined, empresas: [] };
  if (!filePath) return res;
  if (!fs.existsSync(filePath)) return res;

  const text = fs.readFileSync(filePath, 'utf8');
  const lines = text.split(/\r?\n/).map(l => l.trim());

  const dayMap = new Map();
  let mode = 'normal';
  let currentDay = null;

  for (const raw of lines) {
    const line = raw.trim();
    if (!line || line.startsWith('#') || line.startsWith('//')) continue;

    const m = line.match(/^\[?\s*DIA\s+(\d{1,2})\s*\]?:?$/i);
    if (m) {
      currentDay = parseInt(m[1], 10);
      if (!dayMap.has(currentDay)) dayMap.set(currentDay, []);
      mode = 'normal';
      continue;
    }

    if (line.startsWith('--')) {
      if (/^--empresas\b/i.test(line)) {
        mode = 'empresas';
        continue;
      } else {
        mode = 'normal';
      }
      const parts = line.split(/\s+/);
      const key = parts[0].toLowerCase();
      const val = parts.slice(1).join(' ').trim();

      if (key === '--start') res.start = val;
      else if (key === '--end') res.end = val;
      else if (key === '--municipio') res.municipio = val;
      else if (key === '--out') res.out = val;

      continue;
    }

    if (mode === 'empresas') {
      const clean = line.replace(/;+\s*$/, '');
      const code = zeroPad5(clean);
      if (!code) continue;
      if (currentDay != null) {
        dayMap.get(currentDay).push(code);
      } else {
        res.empresas.push(code);
      }
    }
  }

  if (dayMap.size > 0) {
    const today = getDayInTimezone('America/Sao_Paulo', argv.day);
    const chosen = dayMap.get(today);
    if (Array.isArray(chosen) && chosen.length) {
      res.empresas = chosen;
    } else {
      res.empresas = [];
    }
  } else if (!res.empresas.length) {
    const allCodes = lines
      .filter(l => !l.startsWith('--'))
      .join(' ')
      .split(';')
      .map(s => s.trim())
      .map(zeroPad5)
      .filter(Boolean);
    if (allCodes.length) res.empresas = allCodes;
  }

  return res;
}

// ---------------- PowerShell mover ----------------
async function runPowerShellMover({ logger, outDir }) {
  const enabled  = String(process.env.PS_MOVE_ENABLED || 'false').toLowerCase() === 'true';
  if (!enabled) {
    logger.write('Transferência PowerShell desabilitada (PS_MOVE_ENABLED=false).');
    return { skipped: true };
  }

  const psPath   = process.env.PS_MOVE_PATH;
  if (!psPath || !fs.existsSync(psPath)) {
    logger.write(`ATENÇÃO: PS_MOVE_ENABLED=true mas PS_MOVE_PATH não existe: ${psPath || '(vazio)'}`);
    return { skipped: true };
  }

  const args = ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', psPath];

  const extra = splitCliArgs(process.env.PS_EXTRA_ARGS || '');
  if (extra.length) args.push(...extra);

  const hasSource = extra.join(' ').toLowerCase().includes('-source');
  const hasMap    = extra.join(' ').toLowerCase().includes('-map');

  const sourceDir = process.env.PS_SOURCE_DIR || outDir;
  const mapPath   = process.env.PS_MAP_PATH;

  if (!hasSource && sourceDir) args.push('-Source', sourceDir);
  if (!hasMap && mapPath)      args.push('-Map', mapPath);

  logger.write(`Executando PowerShell: powershell.exe ${args.join(' ')}`);

  return new Promise((resolve, reject) => {
    const child = spawn('powershell.exe', args, { windowsHide: true });

    child.stdout.on('data', (d) => logger.write(`[PS] ${d.toString().trimEnd()}`));
    child.stderr.on('data', (d) => logger.write(`[PS:ERR] ${d.toString().trimEnd()}`));

    child.on('error', (err) => {
      logger.write(`ERRO ao iniciar PowerShell: ${err.message || err}`);
      reject(err);
    });

    child.on('close', (code) => {
      if (code === 0) {
        logger.write('PowerShell finalizado com sucesso (exitCode=0).');
        resolve({ code: 0 });
      } else {
        logger.write(`PowerShell finalizado com falha (exitCode=${code}).`);
        // Para não derrubar o processo principal, resolva ao invés de rejeitar:
        // resolve({ code });
        reject(new Error(`PowerShell exitCode=${code}`));
      }
    });
  });
}

// ---------------- RUN ----------------
async function run() {
  ensureDirSync(DEFAULT_LOG_DIR);
  const logger = new Logger(DEFAULT_LOG_DIR);

  try {
    const cfgPath = argv.cfg || DEFAULT_CONFIG_PATH;
    const cfg = loadConfigFile(cfgPath);

    const start = argv.start || cfg.start || null;
    const end   = argv.end   || cfg.end   || null;
    const municipio =
      argv.municipio != null ? argv.municipio :
      (cfg.municipio != null ? cfg.municipio : null);
    const outDir = argv.out || cfg.out || DEFAULT_OUT_DIR;

    let empresas = [];
    if (argv.empresas) {
      empresas = String(argv.empresas).split(';').map(s => zeroPad5(s)).filter(Boolean);
    } else {
      empresas = cfg.empresas || [];
    }

    logger.write('===== INÍCIO =====');
    logger.write(`Origem cfg='${cfgPath}' | Out='${outDir}' | Start='${start}' | End='${end}' | Municipio='${municipio}'`);
    logger.write(`Dia considerado (America/Sao_Paulo): ${getDayInTimezone('America/Sao_Paulo', argv.day)}`);
    logger.write(`Empresas alvo: ${empresas.join(', ') || '(nenhuma)'}`);

    if (!empresas || empresas.length === 0) {
      throw new Error('Nenhuma empresa informada (verifique blocos [DIA X] no params.txt, o dia atual ou use --day para teste).');
    }

    logger.write('Conectando ao SQL Server...');
    const pool = await getPool();
    logger.write('Conexão OK.');

    const startAll = Date.now();
    const resultados = [];
    let skipped = 0;

    try {
      for (const code of empresas) {
        const code5 = zeroPad5(code);
        if (!code5 || /^0+$/.test(code5)) {
          logger.write(`Código inválido: "${code}". Pulando...`);
          skipped++;
          continue;
        }

        const exists = await checkCompanyTableExists(pool, code5);
        if (!exists) {
          logger.write(`Empresa ${code} não encontrada (sem objeto WFiscal.M${code}). Pulando...`);
          skipped++;
          continue;
        }

        logger.write(`--- Empresa ${code5} ---`);
        const t0 = Date.now();
        try {
          const r = await exportCompany(pool, code5, { start, end, municipio: municipio === 'null' ? null : municipio, outDir }, logger);
          resultados.push({ code5, ...r });
          logger.write(`Arquivo gerado: ${r.outFile}`);
        } catch (err) {
          logger.write(`ERRO ao processar ${code5}: ${err && err.message ? err.message : err}`);
          skipped++;
        }
        const tEnd = Date.now();
        logger.write(`Tempo empresa ${code5}: ${formatMs(tEnd - t0)}`);
      }
    } finally {
      await pool.close();
    }

    const endAll = Date.now();
    const totalMs = endAll - startAll;

    logger.write('===== RESUMO GERAL =====');
    logger.write(`Empresas solicitadas: ${empresas.length}`);
    logger.write(`Empresas processadas: ${resultados.length}`);
    logger.write(`Empresas puladas (não encontradas/erro): ${skipped}`);
    resultados.forEach(r => {
      logger.write(`- ${r.code5}: Saída=${formatMs(r.tempoSaida)}, Entrada=${formatMs(r.tempoEntrada)}, Total=${formatMs(r.tempoTotalEmpresa)} | Arquivo: ${r.outFile}`);
    });
    logger.write(`Tempo TOTAL do processo: ${formatMs(totalMs)}`);

    // ----------------- ETAPA 2: mover relatórios com PowerShell -----------------
    try {
      await runPowerShellMover({ logger, outDir });
    } catch (psErr) {
      logger.write(`Falha na transferência PowerShell: ${psErr && psErr.message ? psErr.message : psErr}`);
      // não derruba o processo
    }

    // ----------------- ETAPA 3: análise Cód. Oper. Contábil -----------------
    const extraHtmlParts = [];
    const extraTextParts = [];

    try {
      const analysis1 = await analyzeCodOperContabil({ resultados, logger });
      if (analysis1.failingCodes.length > 0) {
        const lista = analysis1.failingCodes.join(' - ');
        logger.write(`Empresas sem o Cód. Oper. Contábil = 1 (Entrada e/ou Saída): ${lista}`);
        extraHtmlParts.push(`
          <h3 style="margin-top:16px">Empresas sem o Cód. Oper. Contábil</h3>
          <p><strong>${lista}</strong></p>
        `);
        extraTextParts.push([
          'Empresas sem o Cód. Oper. Contábil',
          lista,
          ''
        ].join('\n'));
      } else {
        const msgH = '<h3 style="margin-top:16px">Empresas sem o Cód. Oper. Contábil</h3><p><strong>Nenhuma empresa sem Cód. Oper. Contábil</strong></p>';
        const msgT = 'Empresas sem o Cód. Oper. Contábil\nNenhuma empresa sem Cód. Oper. Contábil\n';
        logger.write('Todas as empresas com Cód. Oper. Contábil = 1 em Entrada e Saída.');
        extraHtmlParts.push(msgH);
        extraTextParts.push(msgT);
      }
    } catch (anErr) {
      logger.write(`Falha na análise do Cód. Oper. Contábil: ${anErr?.message || anErr}`);
      extraHtmlParts.push('<p style="color:#c62828"><strong>Falha ao executar a análise do Cód. Oper. Contábil.</strong></p>');
      extraTextParts.push('Falha ao executar a análise do Cód. Oper. Contábil.\n');
    }

    // ----------------- ETAPA 4: análise Notas duplicadas -----------------
    try {
      const analysis2 = await analyzeNotasDuplicadas({ resultados, logger });
      if (analysis2.failingCodes.length > 0) {
        const lista = analysis2.failingCodes.join(' - ');
        logger.write(`Notas duplicadas detectadas em: ${lista}`);
        extraHtmlParts.push(`
          <h3 style="margin-top:16px">Notas duplicadas</h3>
          <p><strong>${lista}</strong></p>
        `);
        extraTextParts.push([
          'Notas duplicadas',
          lista,
          ''
        ].join('\n'));
      } else {
        const msgH = '<h3 style="margin-top:16px">Notas duplicadas</h3><p><strong>Nenhuma empresa com nota duplicada</strong></p>';
        const msgT = 'Notas duplicadas\nNenhuma empresa com nota duplicada\n';
        logger.write('Nenhuma duplicidade de notas encontrada.');
        extraHtmlParts.push(msgH);
        extraTextParts.push(msgT);
      }
    } catch (dupErr) {
      logger.write(`Falha na análise de Notas duplicadas: ${dupErr?.message || dupErr}`);
      extraHtmlParts.push('<p style="color:#c62828"><strong>Falha ao executar a análise de Notas duplicadas.</strong></p>');
      extraTextParts.push('Falha ao executar a análise de Notas duplicadas.\n');
    }

    // ----------------- ETAPA 5: análise Lançamentos por CFOP -----------------
    try {
      const analysis3 = await analyzeLancamentosPorCFOP({ resultados, logger });
      if (analysis3.warning) {
        logger.write(`Aviso CFOP: ${analysis3.warning}`);
      }
      if (analysis3.failingCodes.length > 0) {
        const lista = analysis3.failingCodes.join(' - ');
        logger.write(`Empresas com códigos de lançamentos contábil incorretos: ${lista}`);
        extraHtmlParts.push(`
          <h3 style="margin-top:16px">Empresas com os códigos de lançamentos contábil incorretos</h3>
          <p><strong>${lista}</strong></p>
        `);
        extraTextParts.push([
          'Empresas com os códigos de lançamentos contábil incorretos',
          lista,
          ''
        ].join('\n'));
      } else {
        const msgH = '<h3 style="margin-top:16px">Empresas com os códigos de lançamentos contábil incorretos</h3><p><strong>Nenhuma empresa incorreta</strong></p>';
        const msgT = 'Empresas com os códigos de lançamentos contábil incorretos\nNenhuma empresa incorreta\n';
        logger.write('CFOP x códigos de lançamento: todas as empresas corretas.');
        extraHtmlParts.push(msgH);
        extraTextParts.push(msgT);
      }
    } catch (cfopErr) {
      logger.write(`Falha na análise de Lançamentos por CFOP: ${cfopErr?.message || cfopErr}`);
      extraHtmlParts.push('<p style="color:#c62828"><strong>Falha ao executar a análise de Lançamentos por CFOP.</strong></p>');
      extraTextParts.push('Falha ao executar a análise de Lançamentos por CFOP.\n');
    }

    // ----------------- ETAPA 6 (final): enviar e-mail -----------------
    const extraInfoHtml = extraHtmlParts.join('\n');
    const extraInfoText = extraTextParts.join('\n');
    
    try {
      await sendSummaryEmail({
        logger,
        empresasSolicitadas: empresas,
        resultados,
        skipped,
        outDir,
        logPath: logger.logPath,
        extraInfoHtml,
        extraInfoText
      });
    } catch (mailErr) {
      logger.write(`Falha ao enviar e-mail: ${mailErr?.message || mailErr}`);
    }    

    logger.write('===== FIM =====');
    console.log(`\nLog salvo em: ${logger.logPath}`);
  } catch (e) {
    console.error('ERRO FATAL:', e && e.message ? e.message : e);
    process.exit(1);
  }
}

run();
