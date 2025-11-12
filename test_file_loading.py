"""
Script de teste para verificar se o carregamento de arquivos está funcionando.
"""

from pathlib import Path
from bi_processor import load_bi_strict_multisheet, load_bi_multisheet

print("=" * 60)
print("TESTE DE CARREGAMENTO DE ARQUIVOS")
print("=" * 60)
print()

# Teste 1: Carregar com caminho de arquivo (string)
print("1️⃣ Testando com caminho de arquivo (string)...")
test_file = "temp_bi/01523_2025-09-01_2025-10-01_30-10-2025.xlsx"

if Path(test_file).exists():
    try:
        # Teste com load_bi_strict_multisheet
        result = load_bi_strict_multisheet(test_file, "Teste")
        if result is not None:
            print(f"   ✅ load_bi_strict_multisheet: {len(result)} registros carregados")
        else:
            print("   ⚠️  load_bi_strict_multisheet: retornou None")
    except Exception as e:
        print(f"   ❌ load_bi_strict_multisheet: {e}")

    try:
        # Teste com load_bi_multisheet
        entrada, saida = load_bi_multisheet(test_file)
        if entrada:
            print(f"   ✅ load_bi_multisheet (Entrada): {len(entrada[0])} registros")
        if saida:
            print(f"   ✅ load_bi_multisheet (Saída): {len(saida[0])} registros")
    except Exception as e:
        print(f"   ❌ load_bi_multisheet: {e}")
else:
    print(f"   ⚠️  Arquivo de teste não encontrado: {test_file}")
    print("   💡 Execute a extração primeiro na aba de Extração Alterdata BI")

print()
print("=" * 60)
print("TESTE CONCLUÍDO")
print("=" * 60)
