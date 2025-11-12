# 🪟 Guia Completo: Rodar no Windows

## 📋 Pré-requisitos

- Windows 10 ou superior
- Python 3.8 ou superior
- Acesso à rede do servidor SQL Server

---

## 🚀 Instalação Passo a Passo

### 1️⃣ Instalar Python

**Opção A: Download Direto**

1. Acesse: https://www.python.org/downloads/
2. Baixe Python 3.11 ou superior
3. **IMPORTANTE**: Marque "Add Python to PATH" durante instalação
4. Clique em "Install Now"

**Opção B: Via Microsoft Store**

1. Abra a Microsoft Store
2. Busque por "Python 3.11"
3. Clique em "Obter"

**Verificar instalação:**
```cmd
python --version
```

---

### 2️⃣ Instalar ODBC Driver 18 for SQL Server

**Método Recomendado:**

1. Acesse: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

2. Baixe **ODBC Driver 18 for SQL Server** (escolha a versão correta):
   - **64-bit**: `msodbcsql_18.x.x.x_x64.msi` (mais comum)
   - **32-bit**: `msodbcsql_18.x.x.x_x86.msi`

3. Execute o instalador `.msi` baixado

4. Siga o assistente:
   - Aceite os termos de licença
   - Escolha "Instalação Completa"
   - Clique em "Instalar"

**Link Direto (ODBC 18.4.1):**
```
https://go.microsoft.com/fwlink/?linkid=2249006
```

**Verificar instalação:**

Abra PowerShell e execute:
```powershell
Get-OdbcDriver | Where-Object {$_.Name -like "*SQL Server*"}
```

Deve aparecer algo como:
```
Name                           Platform  Version
----                           --------  -------
ODBC Driver 18 for SQL Server  64-bit    18.x.x.xxxx
```

---

### 3️⃣ Baixar o Projeto

**Opção A: Com Git**
```cmd
cd C:\
git clone https://github.com/seu-usuario/Conferencia-Livro-Razao.git
cd Conferencia-Livro-Razao
```

**Opção B: Download ZIP**
1. Baixe o ZIP do GitHub
2. Extraia para `C:\Conferencia-Livro-Razao`
3. Abra CMD ou PowerShell nessa pasta

---

### 4️⃣ Criar Ambiente Virtual (Recomendado)

```cmd
cd C:\Conferencia-Livro-Razao
python -m venv venv
venv\Scripts\activate
```

Você verá `(venv)` no início da linha.

---

### 5️⃣ Instalar Dependências

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

**Se der erro no pyodbc**, tente:
```cmd
pip install pyodbc --no-cache-dir
```

---

### 6️⃣ Configurar Credenciais (.env)

1. Navegue até `Alterdata_BI\.env`

2. **Importante para Windows**: O caminho do servidor pode usar `\` (barra invertida):

```env
DB_HOST=srvjcatech01\sqljcw
DB_USER=adriano-sql
DB_PASS='wc&EZtHHv9iynTD#'
DB_NAME=ALTERDATA_PACK
```

**Notas:**
- Se a senha tiver caracteres especiais, mantenha entre aspas simples
- Use `\` para instância (ex: `servidor\instancia`)

---

### 7️⃣ Executar o Sistema

```cmd
streamlit run app.py
```

O navegador abrirá automaticamente em: `http://localhost:8501`

**Se não abrir automaticamente:**
- Abra seu navegador
- Acesse: `http://localhost:8501`

---

## 🔧 Configurações Específicas do Windows

### Firewall do Windows

Se o SQL Server estiver em outra máquina, libere a porta **1433**:

1. Painel de Controle → Windows Defender Firewall
2. Configurações Avançadas
3. Regras de Entrada → Nova Regra
4. Porta → TCP → 1433
5. Permitir conexão
6. Nome: "SQL Server"

### SQL Server Native Client

Se já tiver **SQL Server Native Client** instalado, o sistema também funcionará.

---

## 🐛 Solução de Problemas

### ❌ Erro: "python não é reconhecido"

**Solução:**
1. Reinstale Python marcando "Add to PATH"
2. Ou adicione manualmente:
   - Painel de Controle → Sistema → Configurações avançadas
   - Variáveis de Ambiente
   - PATH → Adicionar: `C:\Python311` e `C:\Python311\Scripts`

---

### ❌ Erro: "No module named 'pyodbc'"

**Solução:**
```cmd
pip install pyodbc --force-reinstall
```

---

### ❌ Erro: "Data source name not found"

**Causa:** ODBC Driver não instalado corretamente.

**Solução:**
1. Reinstale ODBC Driver 18
2. Verifique com:
   ```powershell
   Get-OdbcDriver
   ```

---

### ❌ Erro: "Login failed for user"

**Causas possíveis:**
1. Usuário/senha incorretos no `.env`
2. Autenticação SQL Server desabilitada
3. Usuário sem permissões

**Solução:**
1. Verifique credenciais no `.env`
2. No SQL Server Management Studio (SSMS):
   - Propriedades do Servidor → Security
   - Marque "SQL Server and Windows Authentication mode"
   - Reinicie SQL Server

---

### ❌ Erro: "A network-related error occurred"

**Causas:**
1. SQL Server não está rodando
2. Firewall bloqueando
3. Instância incorreta

**Solução:**
1. Verifique se SQL Server está rodando:
   - Services.msc → SQL Server (MSSQLSERVER)
2. Teste conexão com SSMS primeiro
3. Confirme nome da instância no `.env`

---

### ❌ Erro: "SSL Provider: The certificate chain was issued by an authority that is not trusted"

**Solução:**
O código já inclui `TrustServerCertificate=yes`, mas se persistir, edite `alterdata_connector.py`:

```python
# Adicione à connection string:
Encrypt=no;
```

---

## 📊 Teste Rápido

Execute o script de diagnóstico:

```cmd
python test_odbc_connection.py
```

Se tudo estiver OK, você verá:
```
✅ pyodbc instalado com sucesso
✅ ODBC Driver 18 for SQL Server
✅ Driver SQL Server encontrado
```

---

## 🎯 Estrutura de Pastas Windows

```
C:\
└── Conferencia-Livro-Razao\
    ├── venv\                    # Ambiente virtual
    ├── Alterdata_BI\
    │   └── .env                 # Credenciais AQUI
    ├── temp_bi\                 # Arquivos gerados
    ├── app.py                   # Aplicação principal
    ├── requirements.txt         # Dependências
    └── ...
```

---

## 🚀 Scripts Úteis para Windows

### Criar script de inicialização (start.bat)

Crie um arquivo `start.bat` na raiz do projeto:

```batch
@echo off
echo Iniciando Sistema de Conferencia Fiscal...
cd /d %~dp0
call venv\Scripts\activate
streamlit run app.py
pause
```

**Uso:** Duplo clique em `start.bat`

---

### Criar atalho na Área de Trabalho

1. Clique direito na Área de Trabalho → Novo → Atalho
2. Localize: `C:\Conferencia-Livro-Razao\start.bat`
3. Nome: "Conferência Fiscal"
4. Escolha um ícone

---

## 📝 Checklist de Instalação

- [ ] Python 3.8+ instalado
- [ ] Python no PATH
- [ ] ODBC Driver 18 instalado
- [ ] Projeto baixado
- [ ] Ambiente virtual criado
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] Arquivo `.env` configurado
- [ ] Teste de conexão funcionando
- [ ] Sistema rodando (`streamlit run app.py`)

---

## 🔒 Segurança no Windows

### Proteger o arquivo .env

1. Clique direito no arquivo `.env`
2. Propriedades → Avançado
3. Marque "Criptografar conteúdo para proteger dados"
4. OK

### Usar autenticação Windows (alternativa)

Se preferir não usar senha no `.env`, configure SQL Server para autenticação Windows:

```python
# Em alterdata_connector.py, modificar connection string:
Trusted_Connection=yes;
# E remover: UID e PWD
```

---

## 📞 Suporte Adicional

### Logs do Windows

Logs ficam em:
```
C:\Users\SeuUsuario\.streamlit\logs\
```

### Verificar versões instaladas

```cmd
python --version
pip list
odbcconf /q /a {SQLGETCONNECTIONPOOLINGMODE}
```

---

## 🎉 Próximos Passos

Após instalação bem-sucedida:

1. Execute: `streamlit run app.py`
2. Acesse: http://localhost:8501
3. Vá para aba **🔄 Extração Alterdata BI**
4. Teste a conexão
5. Extraia dados de uma empresa teste

---

**Última atualização:** Outubro 2025
**Testado em:** Windows 10, Windows 11, Windows Server 2019+
