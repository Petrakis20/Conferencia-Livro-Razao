"""
Script de teste para verificar instalação do ODBC Driver e conexão com SQL Server.
Execute este script para diagnosticar problemas de conexão.
"""

import sys

print("=" * 60)
print("TESTE DE ODBC DRIVER E CONEXÃO SQL SERVER")
print("=" * 60)
print()

# Teste 1: Verificar se pyodbc está instalado
print("1️⃣ Verificando instalação do pyodbc...")
try:
    import pyodbc
    print("   ✅ pyodbc instalado com sucesso")
    print(f"   📦 Versão: {pyodbc.version}")
except ImportError as e:
    print(f"   ❌ pyodbc NÃO instalado: {e}")
    print("   💡 Execute: pip install pyodbc")
    sys.exit(1)

print()

# Teste 2: Listar drivers ODBC disponíveis
print("2️⃣ Drivers ODBC disponíveis:")
try:
    drivers = pyodbc.drivers()
    if drivers:
        for driver in drivers:
            if 'SQL Server' in driver:
                print(f"   ✅ {driver}")
            else:
                print(f"   ℹ️  {driver}")
    else:
        print("   ❌ Nenhum driver ODBC encontrado")
        print("   💡 Instale o ODBC Driver 18 for SQL Server")
except Exception as e:
    print(f"   ❌ Erro ao listar drivers: {e}")

print()

# Teste 3: Verificar se há driver SQL Server
print("3️⃣ Verificando driver SQL Server...")
sql_drivers = [d for d in pyodbc.drivers() if 'SQL Server' in d]
if sql_drivers:
    print(f"   ✅ Driver SQL Server encontrado: {sql_drivers[0]}")
else:
    print("   ❌ Nenhum driver SQL Server encontrado")
    print("   💡 macOS: brew install microsoft/mssql-release/msodbcsql18")
    print("   💡 Windows: Baixar de https://learn.microsoft.com/sql/connect/odbc/")
    sys.exit(1)

print()

# Teste 4: Teste de conexão (opcional)
print("4️⃣ Teste de conexão SQL Server...")
print("   ⚠️  Para testar a conexão, preencha os dados abaixo:")
print()

test_connection = input("   Deseja testar a conexão agora? (s/N): ").strip().lower()

if test_connection == 's':
    print()
    server = input("   Servidor (ex: servidor\\instancia): ").strip()
    database = input("   Database: ").strip()
    user = input("   Usuário: ").strip()

    import getpass
    password = getpass.getpass("   Senha: ")

    if not all([server, database, user, password]):
        print("   ⚠️  Campos obrigatórios não preenchidos. Teste cancelado.")
    else:
        print()
        print("   Conectando...")
        try:
            # Tenta com driver 18 primeiro
            preferred_drivers = [
                "ODBC Driver 18 for SQL Server",
                "ODBC Driver 17 for SQL Server",
                "ODBC Driver 13 for SQL Server"
            ]

            driver = None
            for d in preferred_drivers:
                if d in sql_drivers:
                    driver = d
                    break

            if not driver:
                driver = sql_drivers[0]

            # Monta string de conexão
            if '\\' in server:
                server_part, instance = server.split('\\', 1)
                conn_str = f"DRIVER={{{driver}}};SERVER={server_part}\\{instance};DATABASE={database};UID={user};PWD={password};TrustServerCertificate=yes"
            else:
                conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};UID={user};PWD={password};TrustServerCertificate=yes"

            print(f"   Driver usado: {driver}")

            conn = pyodbc.connect(conn_str, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]

            print("   ✅ CONEXÃO BEM-SUCEDIDA!")
            print(f"   📊 SQL Server Version: {version[:80]}...")

            conn.close()

        except Exception as e:
            print(f"   ❌ ERRO NA CONEXÃO: {e}")
            print()
            print("   💡 Dicas:")
            print("      - Verifique se o servidor está acessível")
            print("      - Confirme usuário e senha")
            print("      - Verifique permissões SQL Server")
            print("      - Confirme que a porta está aberta (1433)")
else:
    print("   ⏭️  Teste de conexão pulado.")

print()
print("=" * 60)
print("TESTE CONCLUÍDO")
print("=" * 60)
