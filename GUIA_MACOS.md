# 🚀 Guia de Execução - macOS

Este guia ensina como rodar o projeto **Sistema de Conferência Input Fiscal** no seu terminal macOS.

---

## 📋 Pré-requisitos (Já Instalados ✅)

- ✅ Python 3.8+
- ✅ Homebrew
- ✅ UnixODBC
- ✅ ODBC Driver 18 for SQL Server

---

## 🎯 Opção 1: Usar o Script Automático (RECOMENDADO)

### Passo a Passo:

1. **Abra o Terminal**

2. **Navegue até a pasta do projeto:**
   ```bash
   cd ~/Documents/GitHub/Conferencia-Livro-Razao
   ```

3. **Execute o script:**
   ```bash
   ./start.sh
   ```

4. **Acesse no navegador:**
   - Abra: `http://localhost:8501`

5. **Para parar o servidor:**
   - Pressione `Ctrl + C` no terminal

---

## 🛠️ Opção 2: Comandos Manuais

Se preferir executar os comandos manualmente:

### Primeira vez (apenas uma vez):

```bash
# 1. Navegue até a pasta do projeto
cd ~/Documents/GitHub/Conferencia-Livro-Razao

# 2. Crie o ambiente virtual (se não existir)
python3 -m venv venv

# 3. Instale as dependências
./venv/bin/pip install -r requirements.txt
```

### Toda vez que quiser rodar:

```bash
# 1. Navegue até a pasta do projeto
cd ~/Documents/GitHub/Conferencia-Livro-Razao

# 2. Execute o Streamlit
./venv/bin/streamlit run app.py
```

### Para parar:

- Pressione `Ctrl + C` no terminal

---

## 🔧 Comandos Úteis

### Verificar se o Python está instalado:
```bash
python3 --version
```

### Verificar se as dependências estão instaladas:
```bash
./venv/bin/pip list
```

### Atualizar as dependências:
```bash
./venv/bin/pip install -r requirements.txt --upgrade
```

### Limpar o cache do Streamlit:
```bash
./venv/bin/streamlit cache clear
```

---

## 🌐 URLs de Acesso

Após iniciar o servidor, acesse:

- **Local:** http://localhost:8501
- **Rede:** http://192.168.0.98:8501 (acessível por outros dispositivos na mesma rede)

---

## 🐛 Solução de Problemas

### Erro: "comando não encontrado: python3"
```bash
# Instale o Python via Homebrew
brew install python3
```

### Erro: "Permission denied"
```bash
# Dê permissão de execução ao script
chmod +x start.sh
```

### Erro: "porta 8501 já está em uso"
```bash
# Encerre o processo que está usando a porta
lsof -ti:8501 | xargs kill -9

# Ou use outra porta
./venv/bin/streamlit run app.py --server.port 8502
```

### Erro de conexão ODBC
```bash
# Reinstale o UnixODBC e o ODBC Driver
brew reinstall unixodbc
brew reinstall msodbcsql18
```

---

## 📁 Estrutura de Pastas

```
Conferencia-Livro-Razao/
├── start.sh              ← Script de inicialização (USE ESTE!)
├── app.py                ← Aplicação principal
├── requirements.txt      ← Dependências Python
├── venv/                 ← Ambiente virtual (criado automaticamente)
└── Alterdata_BI/
    └── .env              ← Credenciais do SQL Server (configure se necessário)
```

---

## ⚙️ Configuração Adicional (Opcional)

### Se for usar a Extração Alterdata BI:

1. **Crie o arquivo de credenciais:**
   ```bash
   nano Alterdata_BI/.env
   ```

2. **Adicione suas credenciais:**
   ```env
   DB_HOST=seu_servidor\instancia
   DB_USER=seu_usuario
   DB_PASS=sua_senha
   DB_NAME=ALTERDATA_PACK
   ```

3. **Salve:** 
   - Pressione `Ctrl + O` (salvar)
   - Pressione `Enter`
   - Pressione `Ctrl + X` (sair)

---

## 📞 Atalhos Rápidos

### Comando completo em uma linha:
```bash
cd ~/Documents/GitHub/Conferencia-Livro-Razao && ./start.sh
```

### Criar um alias (adicione no seu `~/.zshrc`):
```bash
alias conferencia="cd ~/Documents/GitHub/Conferencia-Livro-Razao && ./start.sh"
```

Depois disso, você pode simplesmente digitar `conferencia` de qualquer lugar!

---

**Versão:** 2.0  
**Última atualização:** Janeiro 2026  
**Sistema:** macOS
