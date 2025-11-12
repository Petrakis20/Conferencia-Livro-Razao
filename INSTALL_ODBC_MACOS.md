# 🔧 Guia de Instalação: ODBC Driver para SQL Server (macOS)

## ⚡ Instalação Rápida

### Opção 1: Via Homebrew (Recomendado)

```bash
# 1. Adicionar repositório Microsoft
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release

# 2. Instalar ODBC Driver 18
HOMEBREW_NO_AUTO_UPDATE=1 brew install microsoft/mssql-release/msodbcsql18

# 3. Aceitar EULA durante instalação
# Pressione ENTER para ler e digite "YES" quando solicitado
```

### Opção 2: Download Direto (se Homebrew falhar)

1. Acesse: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
2. Baixe o instalador para macOS
3. Execute o arquivo `.pkg` baixado
4. Siga o assistente de instalação

---

## ✅ Verificar Instalação

Após instalar, execute o script de teste:

```bash
python test_odbc_connection.py
```

**Saída esperada:**
```
1️⃣ Verificando instalação do pyodbc...
   ✅ pyodbc instalado com sucesso
   📦 Versão: 5.x.x

2️⃣ Drivers ODBC disponíveis:
   ✅ ODBC Driver 18 for SQL Server

3️⃣ Verificando driver SQL Server...
   ✅ Driver SQL Server encontrado: ODBC Driver 18 for SQL Server
```

---

## 🐛 Troubleshooting

### Erro: "pyodbc.Error: Data source name not found"

**Solução 1**: Reinstalar o driver
```bash
brew reinstall microsoft/mssql-release/msodbcsql18
```

**Solução 2**: Verificar drivers disponíveis
```python
import pyodbc
print(pyodbc.drivers())
```

Se não aparecer nenhum driver SQL Server, reinstale usando a Opção 2 (Download Direto).

---

### Erro: "module 'pyodbc' has no attribute 'drivers'"

**Causa**: pyodbc não instalado corretamente

**Solução**:
```bash
pip uninstall pyodbc
pip install pyodbc --no-cache-dir
```

---

### Erro: "SSL connection error"

**Causa**: Certificado SSL não confiável

**Solução**: O código já inclui `TrustServerCertificate=yes`. Se persistir:

1. Verifique se o servidor SQL permite conexões não-SSL
2. Ou obtenha o certificado correto do servidor

---

### Instalação do Homebrew travou/demorou muito

**Solução**:

1. Cancele a instalação (Ctrl+C)
2. Limpe o cache do Homebrew:
   ```bash
   brew cleanup
   rm -rf $(brew --cache)
   ```
3. Tente novamente com auto-update desabilitado:
   ```bash
   HOMEBREW_NO_AUTO_UPDATE=1 brew install microsoft/mssql-release/msodbcsql18
   ```

---

## 📋 Instalação Completa (Passo a Passo Detalhado)

### 1. Instalar Homebrew (se não tiver)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Adicionar repositório Microsoft

```bash
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
```

**Saída esperada:**
```
==> Tapping microsoft/mssql-release
Cloning into '/opt/homebrew/Library/Taps/microsoft/homebrew-mssql-release'...
Tapped 52 formulae
```

### 3. Instalar ODBC Driver

```bash
HOMEBREW_NO_AUTO_UPDATE=1 brew install microsoft/mssql-release/msodbcsql18
```

**Durante a instalação**, você verá:
```
The license terms for this product can be downloaded from
https://aka.ms/odbc18eula and found in
/opt/homebrew/share/doc/msodbcsql18/LICENSE.txt
Enter YES to accept the license or anything else to terminate the installation.
```

Digite: **YES** e pressione ENTER

### 4. Instalar dependências Python

```bash
pip install pyodbc
```

### 5. Testar instalação

```bash
python test_odbc_connection.py
```

---

## 🎯 Comandos Úteis

### Verificar versão instalada
```bash
brew list --versions msodbcsql18
```

### Listar drivers instalados
```python
python -c "import pyodbc; print('\n'.join(pyodbc.drivers()))"
```

### Desinstalar e reinstalar
```bash
brew uninstall msodbcsql18
brew cleanup
HOMEBREW_NO_AUTO_UPDATE=1 brew install microsoft/mssql-release/msodbcsql18
```

---

## 📞 Suporte

Se mesmo após seguir este guia você ainda tiver problemas:

1. Verifique a versão do macOS (requer 10.14+)
2. Verifique a arquitetura (ARM/M1/M2 ou Intel)
3. Consulte a documentação oficial: https://learn.microsoft.com/sql/connect/odbc/

---

**Última atualização**: Outubro 2025
