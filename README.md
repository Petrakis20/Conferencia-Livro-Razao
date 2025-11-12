# 📊 Sistema de Conferência Input Fiscal

Sistema automatizado para análise e conferência de dados fiscais do Alterdata, com validação de CFOPs e comparação BI × Razão.

---

## 🚀 Início Rápido

### Windows
1. Siga o guia completo: **[GUIA_WINDOWS.md](GUIA_WINDOWS.md)**
2. Ou simplesmente execute: **`start.bat`** (duplo clique)

### macOS/Linux
1. Instale dependências: `pip install -r requirements.txt`
2. Execute: `streamlit run app.py`
3. Veja: [INSTALL_ODBC_MACOS.md](INSTALL_ODBC_MACOS.md) para instalar ODBC Driver

---

## 📚 Documentação

| Documento | Descrição |
|-----------|-----------|
| **[GUIA_WINDOWS.md](GUIA_WINDOWS.md)** | 🪟 Guia completo de instalação e uso no Windows |
| **[README_ALTERDATA.md](README_ALTERDATA.md)** | 🔄 Documentação completa da extração Alterdata BI |
| **[INSTALL_ODBC_MACOS.md](INSTALL_ODBC_MACOS.md)** | 🍎 Instalação do ODBC Driver no macOS |

---

## ✨ Funcionalidades

### 🔄 Extração Alterdata BI
- Conexão direta ao SQL Server do Alterdata
- Extração automática de dados de Entrada e Saída
- Validação de empresas por período
- Geração de arquivos Excel compatíveis

### ① Análise do BI (CFOP × Base)
- Validação de CFOPs contra base de referência
- Detecção de códigos de lançamento incorretos
- Identificação de CFOPs não cadastrados
- Métricas e KPIs visuais

### ② Conferência BI × Razão
- Comparação automática de lançamentos
- Identificação de divergências
- Separação de serviços prestados
- Relatórios detalhados

### ③ Conferência Simples Nacional
- Validação de Livro de ICMS × Lote Contábil
- Suporte a ICMS e ICMS ST
- Análise de PDF e TXT

---

## 🔧 Requisitos

### Todos os Sistemas
- Python 3.8 ou superior
- Navegador web moderno

### Windows
- ODBC Driver 18 for SQL Server
- Acesso à rede do SQL Server

### macOS/Linux
- ODBC Driver 18 for SQL Server
- UnixODBC (instalado automaticamente)

---

## ⚙️ Configuração

### 1. Credenciais SQL Server

Edite `Alterdata_BI/.env`:

```env
DB_HOST=seu_servidor\instancia
DB_USER=seu_usuario
DB_PASS=sua_senha
DB_NAME=ALTERDATA_PACK
```

⚠️ **Importante**: Não commite este arquivo no Git!

### 2. Base de CFOPs

O arquivo `cfop_base.json` na raiz do projeto contém os mapeamentos de CFOPs.

---

## 📖 Como Usar

### Opção 1: Windows (Recomendado)
```batch
# Duplo clique em:
start.bat
```

### Opção 2: Linha de Comando
```bash
# Criar ambiente virtual (primeira vez)
python -m venv venv

# Ativar ambiente virtual
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Executar sistema
streamlit run app.py
```

### Opção 3: Python Direto
```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 🎯 Fluxo de Trabalho

```
1. Extração (Aba 🔄)
   ↓
   Conecta ao Alterdata → Extrai dados → Gera Excel
   ↓
2. Análise CFOP (Aba ①)
   ↓
   Valida CFOPs → Identifica problemas → Gera relatório
   ↓
3. Conferência BI × Razão (Aba ②)
   ↓
   Compara lançamentos → Detecta divergências → Relatório final
```

---

## 🐛 Solução de Problemas

### Windows
Consulte [GUIA_WINDOWS.md](GUIA_WINDOWS.md) - Seção "Solução de Problemas"

### Erro: "Credenciais não encontradas"
- Verifique se `Alterdata_BI/.env` existe e está configurado corretamente

### Erro: "ODBC Driver não encontrado"
- Windows: Instale ODBC Driver 18 ([link](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server))
- macOS: Siga [INSTALL_ODBC_MACOS.md](INSTALL_ODBC_MACOS.md)

### Erro de conexão SQL Server
1. Verifique se SQL Server está rodando
2. Teste conexão com SQL Server Management Studio (SSMS)
3. Confirme credenciais no `.env`
4. Verifique firewall (porta 1433)

---

## 📦 Estrutura do Projeto

```
Conferencia-Livro-Razao/
├── app.py                      # Aplicação principal Streamlit
├── alterdata_connector.py      # Conexão SQL Server
├── company_validator.py        # Validação de empresas
├── bi_processor.py            # Processamento de BI
├── razao_processor.py         # Processamento de Razão
├── cfop_analyzer.py           # Análise de CFOPs
├── simples_nacional.py        # Conferência Simples Nacional
├── ui_components.py           # Componentes de interface
├── utils.py                   # Funções utilitárias
├── cfop_base.json            # Base de CFOPs
├── requirements.txt          # Dependências Python
├── start.bat                 # Script de inicialização Windows
├── Alterdata_BI/
│   ├── .env                  # Credenciais (não commitar!)
│   └── params.txt            # Configuração de empresas
└── temp_bi/                  # Arquivos gerados (temporário)
```

---

## 🔒 Segurança

- ✅ Credenciais armazenadas em `.env` (fora do Git)
- ✅ Senha nunca exibida na interface
- ✅ Conexões com `TrustServerCertificate` para ambientes internos
- ✅ Validação de permissões por empresa e período

---

## 📊 Tecnologias

- **Streamlit** - Interface web interativa
- **Pandas** - Processamento de dados
- **pyODBC** - Conexão SQL Server
- **openpyxl** - Leitura/escrita Excel
- **ReportLab** - Geração de PDFs
- **pypdf** - Leitura de PDFs

---

## 📝 Licença

Uso interno. Todos os direitos reservados.

---

## 📞 Suporte

- 📖 Documentação completa: [README_ALTERDATA.md](README_ALTERDATA.md)
- 🪟 Guia Windows: [GUIA_WINDOWS.md](GUIA_WINDOWS.md)
- 🍎 Guia macOS: [INSTALL_ODBC_MACOS.md](INSTALL_ODBC_MACOS.md)

---

**Versão:** 2.0
**Última atualização:** Outubro 2025
**Compatível com:** Windows 10+, macOS 10.14+, Linux (Ubuntu 20.04+)
