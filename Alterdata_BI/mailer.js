// mailer.js
// Responsável por montar e enviar o e-mail de resumo do processamento.
// Usa Nodemailer. Configuração via variáveis de ambiente (ver .env abaixo).

const fs = require('fs');
const nodemailer = require('nodemailer');

function parseList(val) {
  if (!val) return [];
  return String(val)
    .split(/[,;]+/)
    .map(s => s.trim())
    .filter(Boolean);
}

function getSaoPauloNow() {
  const now = new Date();
  const sp = new Date(now.toLocaleString('en-US', { timeZone: 'America/Sao_Paulo' }));
  const y = sp.getFullYear();
  const m = String(sp.getMonth() + 1).padStart(2, '0');
  const d = String(sp.getDate()).padStart(2, '0');
  const hh = String(sp.getHours()).padStart(2, '0');
  const mm = String(sp.getMinutes()).padStart(2, '0');
  return { sp, stamp: `${y}-${m}-${d} ${hh}:${mm} BRT` };
}

function summarize(resultados) {
  // empresas finalizadas = código da tabela (code5), e opcionalmente quantidades/arquivos
  const empresas = resultados.map(r => r.code5);
  return { empresas };
}

function buildHtml({ stamp, empresas, empresasSolicitadas, skipped, outDir, extraHtml }) {
  const lista = empresas.length ? empresas.join(' - ') : '(nenhuma)';
  const reqTotal = empresasSolicitadas?.length || 0;

  return `
  <div style="font-family:Segoe UI,Roboto,Arial,sans-serif;font-size:14px;line-height:1.45;color:#111">
    <h2 style="margin:0 0 8px">BI Contábil – Processamento concluído</h2>
    <p style="margin:0 0 12px;color:#555">Data/Hora (America/Sao_Paulo): <strong>${stamp}</strong></p>

    <h3 style="margin:16px 0 6px">Empresas finalizadas:</h3>
    <p style="margin:0 0 12px"><strong>${lista}</strong></p>

    <table style="border-collapse:collapse">
      <tr>
        <td style="padding:6px 10px;border:1px solid #ddd;background:#f7f7f7">Solicitadas</td>
        <td style="padding:6px 10px;border:1px solid #ddd">${reqTotal}</td>
      </tr>
      <tr>
        <td style="padding:6px 10px;border:1px solid #ddd;background:#f7f7f7">Concluídas</td>
        <td style="padding:6px 10px;border:1px solid #ddd">${empresas.length}</td>
      </tr>
      <tr>
        <td style="padding:6px 10px;border:1px solid #ddd;background:#f7f7f7">Erro</td>
        <td style="padding:6px 10px;border:1px solid #ddd">${skipped}</td>
      </tr>
    </table>

    ${extraHtml || ''}

    <p style="margin-top:16px;color:#777">Mensagem automática • BI Contábil</p>
  </div>`;
}

function buildText({ stamp, empresas, empresasSolicitadas, skipped, outDir, extraText }) {
  const lista = empresas.length ? empresas.join(' - ') : '(nenhuma)';
  const reqTotal = empresasSolicitadas?.length || 0;

  return [
    `BI Contábil – Processamento concluído`,
    `Data/Hora (America/Sao_Paulo): ${stamp}`,
    ``,
    `Empresas finalizadas:`,
    lista,
    ``,
    `Solicitadas: ${reqTotal}`,
    `Concluídas: ${empresas.length}`,
    `Puladas/Erro: ${skipped}`,
    `Pasta de saída: ${outDir || '(padrão)'}`,
    ``,
    extraText || ''
  ].join('\n');
}

async function createTransport() {
  const host   = process.env.SMTP_HOST;
  const port   = Number(process.env.SMTP_PORT || 587);
  const secure = String(process.env.SMTP_SECURE || 'false').toLowerCase() === 'true';
  const user   = process.env.SMTP_USER;
  const pass   = process.env.SMTP_PASS;

  if (!host) throw new Error('SMTP_HOST não definido');
  if (!user) throw new Error('SMTP_USER não definido');
  if (!pass) throw new Error('SMTP_PASS não definido');

  return nodemailer.createTransport({
    host,
    port,
    secure,
    auth: { user, pass },
    tls: {
      // Permite certificados self-signed se necessário:
      rejectUnauthorized: String(process.env.SMTP_TLS_REJECT_UNAUTHORIZED || 'false').toLowerCase() === 'true'
    }
  });
}

/**
 * Envia o e-mail de resumo do processamento.
 * @param {Object} payload
 * @param {string[]} payload.empresasSolicitadas - lista original do job
 * @param {Array<{code5:string,outFile:string}>} payload.resultados - concluidas
 * @param {number} payload.skipped - quantas falharam/puladas
 * @param {string} payload.outDir - pasta onde salvou os .xlsx
 * @param {string} payload.logPath - caminho do arquivo de log para anexar (opcional)
 * @param {string} [payload.extraInfo] - texto adicional opcional
 * @param {object} [payload.logger] - logger opcional (usa console em fallback)
 */
async function sendSummaryEmail(payload) {
  const logger = payload?.logger || { write: console.log };
  const mailTo = parseList(process.env.MAIL_TO);
  const mailCc = parseList(process.env.MAIL_CC);
  const mailBcc = parseList(process.env.MAIL_BCC);

  if (!mailTo.length && !mailCc.length && !mailBcc.length) {
    logger.write('MAIL_TO/CC/BCC vazios — e-mail de resumo não será enviado.');
    return { skipped: true };
  }

  const from = process.env.MAIL_FROM || process.env.SMTP_USER;
  const prefix = process.env.MAIL_SUBJECT_PREFIX || 'BI Contábil';
  const { stamp } = getSaoPauloNow();
  const { empresas } = summarize(payload.resultados || []);

  const html = buildHtml({
    stamp,
    empresas,
    empresasSolicitadas: payload.empresasSolicitadas,
    skipped: payload.skipped || 0,
    outDir: payload.outDir,
    extraHtml: payload.extraInfoHtml
  });

  const text = buildText({
    stamp,
    empresas,
    empresasSolicitadas: payload.empresasSolicitadas,
    skipped: payload.skipped || 0,
    outDir: payload.outDir,
    extraText: payload.extraInfoText
  });

  const subject = `${prefix} – Processamento concluído (${stamp})`;

  const attachments = [];
  if (payload.logPath && fs.existsSync(payload.logPath)) {
    attachments.push({
      filename: require('path').basename(payload.logPath),
      path: payload.logPath
    });
  }

  const transporter = await createTransport();

  const info = await transporter.sendMail({
    from,
    to: mailTo,
    cc: mailCc.length ? mailCc : undefined,
    bcc: mailBcc.length ? mailBcc : undefined,
    subject,
    text,
    html,
    attachments
  });

  logger.write(`E-mail enviado: ${info.messageId}`);
  return { messageId: info.messageId };
}

module.exports = { sendSummaryEmail };