# 🔄 Integração Alterdata BI - Guia de Uso

## 📋 Visão Geral

A nova funcionalidade de **Extração Alterdata BI** permite conectar-se diretamente ao banco de dados SQL Server do Alterdata e extrair relatórios de BI automaticamente, eliminando a necessidade de exportação manual.

## ✨ Funcionalidades

- ✅ Conexão direta ao SQL Server do Alterdata
- ✅ Validação automática de empresas por período (baseado em params.txt)
- ✅ Extração de dados de Entrada e Saída
- ✅ Geração automática de arquivo Excel compatível com as abas de análise
- ✅ Integração automática com "① Análise do BI" e "② Conferência BI × Razão"

---

## 🚀 Como Usar

### 1️⃣ Acesse a Aba "🔄 Extração Alterdata BI"

Esta é a primeira aba do sistema.

### 2️⃣ Verificar Credenciais SQL Server

As credenciais são carregadas automaticamente do arquivo `Alterdata_BI/.env`:

- **DB_HOST**: Servidor SQL (ex: `srvjcatech01\sqljcw`)
- **DB_NAME**: Nome do banco (ex: `ALTERDATA_PACK`)
- **DB_USER**: Usuário SQL Server
- **DB_PASS**: Senha do usuário

💡 **Dica**: Use o botão "🔌 Testar Conexão" para validar a conexão antes de extrair.

🔒 **Segurança**: As credenciais não são expostas na interface, apenas lidas do arquivo `.env`.

### 3️⃣ Configure o Arquivo .env (Primeira Vez)

Edite o arquivo `Alterdata_BI/.env` com as credenciais corretas:

```env
DB_HOST=srvjcatech01\sqljcw
DB_USER=seu_usuario
DB_PASS=sua_senha
DB_NAME=ALTERDATA_PACK
```

⚠️ **IMPORTANTE**: Nunca commite o arquivo `.env` com credenciais reais no Git!

### 4️⃣ Selecione o Período e Empresa

- **Data Inicial**: Data de início do período
- **Data Final**: Data final (exclusiva - não incluída)
- **Código da Empresa**: Código de 1 a 5 dígitos (será padronizado automaticamente)

### 5️⃣ Entenda a Validação de Empresas

#### 📅 **Período DIFERENTE do params.txt**
Se você selecionar um período diferente do configurado em `Alterdata_BI/params.txt`, a extração é **LIBERADA** para qualquer empresa.

**Exemplo:**
- `params.txt` tem: 2025-09-01 a 2025-10-01
- Você seleciona: 2025-08-01 a 2025-09-01
- ✅ **Resultado**: Pode processar qualquer empresa

#### 📅 **Período IGUAL ao params.txt**
Se você selecionar **exatamente** o mesmo período do `params.txt`, o sistema verifica se a empresa está nos blocos `[DIA X]`.

**Exemplo:**
- `params.txt` tem: 2025-09-01 a 2025-10-01
- Você seleciona: 2025-09-01 a 2025-10-01
- Sistema verifica: Empresa está no bloco `[DIA 12]`?
  - ✅ **SIM**: Extração liberada
  - ❌ **NÃO**: Extração bloqueada

### 6️⃣ Extraia os Dados

Clique no botão **"🚀 Extrair Dados e Gerar BI"**

O sistema irá:
1. Conectar ao SQL Server
2. Validar se a empresa existe (tabela `WFiscal.M{código}`)
3. Executar queries de Entrada e Saída
4. Gerar arquivo Excel com 2 abas
5. Salvar em `temp_bi/`

### 7️⃣ Use nas Outras Abas

Após gerar o arquivo, vá para:

- **① Análise do BI**: Checkbox aparecerá para usar o arquivo gerado
- **② Conferência BI × Razão**: Checkbox aparecerá para usar o arquivo gerado

✅ Marque a opção **"Usar arquivo gerado na aba de Extração"** e o sistema carregará automaticamente!

---

## 📊 Estrutura do params.txt

### Formato do Arquivo

```txt
--start 2025-09-01
--end 2025-10-01
--municipio null
--out C:\Relatorios

[DIA 12]
--empresas
1523;
1535;
1536;
...

[DIA 15]
--empresas
1552;
2252;
...
```

### Blocos de Dia

- `[DIA 12]`: Empresas que podem ser processadas no dia 12 do mês
- `[DIA 15]`: Empresas que podem ser processadas no dia 15 do mês
- etc.

### Validação

A validação SOMENTE ocorre quando:
1. Período selecionado = Período do params.txt (start + end exatos)
2. Existe pelo menos um bloco `[DIA X]` configurado

---

## 🔧 Requisitos Técnicos

### Dependências Python

```bash
pip install pyodbc>=5.0.0
```

### Driver ODBC

É necessário ter o **ODBC Driver 17 ou 18 for SQL Server** instalado:

**Windows:**
- Download: [Microsoft ODBC Driver](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

**macOS:**
```bash
# Adicionar repositório Microsoft
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release

# Instalar ODBC Driver 18 (recomendado)
brew install microsoft/mssql-release/msodbcsql18 microsoft/mssql-release/mssql-tools18
```

**Linux (Ubuntu/Debian):**
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18
```

**Verificar instalação:**
```python
import pyodbc
print(pyodbc.drivers())  # Deve listar "ODBC Driver 18 for SQL Server" ou similar
```

---

## 🗂️ Estrutura de Arquivos Gerados

### Nome do Arquivo

Formato: `{código}_{data_inicial}_{data_final}_{data_geração}.xlsx`

**Exemplo:**
```
01523_2025-09-01_2025-10-01_30-10-2025.xlsx
```

### Abas do Excel

1. **Entrada**: Todas as notas fiscais de entrada do período
2. **Saída**: Todas as notas fiscais de saída do período

### Colunas Extraídas (32 colunas)

- Cancelada
- Dt. Escrituração
- Data Emissão
- CFOP
- Tipo CFOP
- Número
- Nome Forn/Cliente
- Valor Contábil
- Vl. ICMS
- Vl. ST
- Vl. IPI
- **Cód. Oper. Contábil**
- **Lanc. Cont. Vl. Contábil**
- **Lanc. Cont. Vl. ICMS**
- **Lanc. Cont. Vl. Subst. Trib.**
- **Lanc. Cont. Vl. IPI**
- Exportado
- Base ST
- Total PIS
- Total CONFINS
- Vl. Base IPI
- % IPI
- IPI Não Aproveitado
- Vl. Base ICMS
- %ICMS
- CST ICMS
- Informações Complementares
- Data da Importação
- Usuário Importador
- CNPJ/CPF forn/Cliente
- Mod.
- Chave de Acesso NFe/CF SAT

---

## ⚠️ Troubleshooting

### Erro: "Empresa não encontrada"

**Causa**: A tabela `WFiscal.M{código}` não existe no banco.

**Solução**: Verifique se o código da empresa está correto e se a empresa existe no Alterdata.

### Erro: "Conexão recusada"

**Causa**: Credenciais inválidas ou servidor inacessível.

**Soluções**:
1. Verifique usuário e senha
2. Confirme que o servidor está acessível
3. Verifique firewall e permissões SQL
4. Use o botão "Testar Conexão" primeiro

### Erro: "ODBC Driver não encontrado"

**Causa**: Driver ODBC não instalado.

**Solução**: Instale o ODBC Driver 17 for SQL Server (veja seção Requisitos Técnicos)

### Validação bloqueando empresa válida

**Causa**: Período selecionado é igual ao params.txt mas empresa não está no bloco correto.

**Soluções**:
1. Altere o período para um mês diferente (ex: mês anterior)
2. Verifique se a empresa está no bloco correto do params.txt
3. Adicione a empresa no bloco apropriado do params.txt

---

## 📝 Notas Importantes

1. **Segurança**: As credenciais são armazenadas de forma segura no arquivo `Alterdata_BI/.env` e nunca expostas na interface.

2. **Performance**: A extração pode levar alguns minutos dependendo do volume de dados.

3. **Armazenamento**: Arquivos são salvos em `temp_bi/` e ficam disponíveis durante a sessão.

4. **Compatibilidade**: O arquivo gerado é 100% compatível com as funcionalidades existentes de análise e conferência.

5. **Params.txt**: O arquivo `Alterdata_BI/params.txt` é lido automaticamente ao abrir a aba de extração.

---

## 🎯 Fluxo Completo Recomendado

1. **Extração** (Aba 🔄)
   - Configure conexão SQL
   - Selecione período e empresa
   - Extraia dados → Gera Excel

2. **Análise CFOP** (Aba ①)
   - Marque "Usar arquivo gerado"
   - Valide CFOPs contra base

3. **Conferência BI × Razão** (Aba ②)
   - Marque "Usar arquivo gerado"
   - Envie arquivos TXT do Razão
   - Compare lançamentos

4. **Livro de ICMS x Lote Contábil** (Aba ③)
   - Use conforme necessário

---

## 📞 Suporte

Para dúvidas ou problemas, consulte a documentação do Alterdata ou entre em contato com o administrador do sistema.

---

**Versão**: 2.0
**Data**: Outubro 2025
**Desenvolvido para**: Sistema de Conferência Input Fiscal
