# Sistema de Conferência Fiscal

Sistema modular para análise e conferência de dados fiscais, com interface web desenvolvida em Streamlit.

## 📁 Estrutura do Projeto

```
conferencia-livro-razao/
├── app.py                      # Aplicação principal (nova versão modular)
├── conferencia-livro-razao.py  # Versão original (manter como backup)
├── utils.py                    # Funções utilitárias gerais
├── cfop_analyzer.py           # Análise e comparação de CFOP
├── bi_processor.py            # Processamento de arquivos BI
├── razao_processor.py         # Processamento de arquivos de Razão
├── simples_nacional.py        # Módulo do Simples Nacional
├── ui_components.py           # Componentes de interface/UI
├── sn_pdf.py                  # Parser de PDFs do Simples Nacional
├── cfop_base.json            # Base de dados CFOP
└── requirements.txt          # Dependências do projeto
```

## 🚀 Como Executar

### Versão Modular (Recomendada)
```bash
streamlit run app.py
```

### Versão Original (Backup)
```bash
streamlit run conferencia-livro-razao.py
```

## 📚 Módulos do Sistema

### 1. **utils.py** - Funções Utilitárias
- Normalização de texto e códigos
- Conversão de valores brasileiros
- Limpeza de dados
- Funções auxiliares de arquivo

### 2. **cfop_analyzer.py** - Análise CFOP
- Carregamento da base CFOP (JSON)
- Comparação de códigos de lançamento
- Validação contra base de dados
- Cálculo de métricas de análise

### 3. **bi_processor.py** - Processamento BI
- Leitura de arquivos BI (Excel/CSV)
- Processamento de Entradas/Saídas/Serviços
- Detecção automática de colunas
- Limpeza e agregação de dados

### 4. **razao_processor.py** - Processamento Razão
- Leitura de arquivos TXT de razão
- Consolidação de múltiplos arquivos
- Comparação BI vs Razão
- Cálculo de divergências

### 5. **simples_nacional.py** - Simples Nacional
- Processamento de PDFs (ICMS/ICMS ST)
- Processamento de TXT contábil
- Mapeamento CFOP → Lançamentos
- Comparação PDF vs TXT

### 6. **ui_components.py** - Interface do Usuário
- Componentes KPI estilizados
- Animação de fogos de artifício 🎆
- Filtros e controles
- Funções de download
- Formatação de tabelas

## 🎯 Funcionalidades Principais

### Aba 1: Análise do BI (CFOP × Base CFOP)
- Validação de códigos de lançamento
- Comparação contra base CFOP
- Identificação de divergências
- KPIs de validação

### Aba 2: Conferência BI × Razão (TXT)
- Processamento de BI (Entradas/Saídas/Serviços)
- Consolidação de arquivos de razão
- Comparação por lançamento
- Análise de divergências

### Aba 3: Simples Nacional
- Análise de PDFs de livros fiscais
- Comparação com lote contábil
- Mapeamento automático via base CFOP
- Validação de consistência

## 🎉 Animações de Sucesso

O sistema inclui uma animação de fogos de artifício que é disparada automaticamente quando:
- **Aba 1**: Todas as análises CFOP estão OK (sem divergências)
- **Aba 2**: Todas as comparações BI × Razão estão OK
- **Aba 3**: Todas as análises do Simples Nacional estão OK

## 📋 Requisitos

Veja o arquivo `requirements.txt` para a lista completa de dependências.

Principais bibliotecas:
- **streamlit**: Interface web
- **pandas**: Manipulação de dados
- **numpy**: Operações numéricas
- **openpyxl/xlrd**: Leitura de Excel

## 🔧 Configuração

1. **Base CFOP**: Configure o caminho do arquivo `cfop_base.json` na sidebar
2. **Arquivos**: Faça upload dos arquivos BI/Razão nas respectivas abas
3. **Análise**: O sistema processará automaticamente e exibirá os resultados

## 🎨 Melhorias da Refatoração

### ✅ Vantagens da Nova Estrutura:
- **Modularidade**: Código organizado em módulos específicos
- **Manutenibilidade**: Fácil localização e edição de funcionalidades
- **Reutilização**: Funções podem ser importadas entre módulos
- **Testabilidade**: Cada módulo pode ser testado independentemente
- **Legibilidade**: Código mais limpo e documentado
- **Escalabilidade**: Fácil adição de novas funcionalidades

### 📁 Separação de Responsabilidades:
- **Lógica de Negócio**: Separada da interface
- **Processamento de Dados**: Isolado em módulos específicos
- **Interface**: Componentes reutilizáveis
- **Utilidades**: Funções comuns centralizadas

## 🔄 Migração

Para migrar da versão original para a modular:
1. Use `app.py` como arquivo principal
2. Mantenha `conferencia-livro-razao.py` como backup
3. Teste todas as funcionalidades na nova versão
4. Configure dependências se necessário

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique a estrutura de arquivos
2. Confirme dependências instaladas
3. Teste com arquivos de exemplo
4. Consulte logs de erro no Streamlit