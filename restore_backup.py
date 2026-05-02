import sqlite3
import shutil
import os
from datetime import datetime

def check_database(db_path):
    """Verifica o conteúdo de um banco de dados"""
    if not os.path.exists(db_path):
        print(f"❌ {db_path} não encontrado!")
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar tabelas importantes
        tables_to_check = ['routines', 'workout_sessions', 'workout_logs', 'exercises', 'routine_exercises']
        
        data = {}
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                data[table] = count
            except sqlite3.OperationalError:
                data[table] = 0
        
        conn.close()
        return data
    except sqlite3.OperationalError as e:
        print(f"⚠️  Erro ao acessar {db_path}: {e}")
        return None

print("=" * 60)
print("VERIFICAÇÃO DE BANCOS DE DADOS - GYMNight")
print("=" * 60)

# Verificar banco atual
print("\n📊 BANCO DE DADOS ATUAL (gymnight.db):")
current_data = check_database('gymnight.db')
if current_data:
    for table, count in current_data.items():
        print(f"  • {table}: {count} registros")
    
    total_current = sum(current_data.values())
    print(f"\n  Total de registros: {total_current}")

# Verificar backup
print("\n📦 BANCO DE DADOS BACKUP (gymnight.db.backup):")
backup_data = check_database('gymnight.db.backup')
if backup_data:
    for table, count in backup_data.items():
        print(f"  • {table}: {count} registros")
    
    total_backup = sum(backup_data.values())
    print(f"\n  Total de registros: {total_backup}")

# Análise e recomendação
print("\n" + "=" * 60)
print("ANÁLISE:")
print("=" * 60)

if current_data and backup_data:
    # Comparar rotinas
    if backup_data['routines'] > current_data['routines']:
        print(f"⚠️  BACKUP tem MAIS rotinas: {backup_data['routines']} vs {current_data['routines']}")
    
    # Comparar sessões de treino
    if backup_data['workout_sessions'] > current_data['workout_sessions']:
        print(f"⚠️  BACKUP tem MAIS sessões: {backup_data['workout_sessions']} vs {current_data['workout_sessions']}")
    
    # Comparar logs de treino
    if backup_data['workout_logs'] > current_data['workout_logs']:
        print(f"⚠️  BACKUP tem MAIS logs: {backup_data['workout_logs']} vs {current_data['workout_logs']}")
    
    if total_backup > total_current:
        print(f"\n✅ RECOMENDAÇÃO: Restaurar do backup!")
        print(f"   Backup tem {total_backup - total_current} registros a mais.")
        
        # Fazer backup do atual antes de restaurar
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_current = f"gymnight.db.before_restore_{timestamp}"
        
        print(f"\n🔄 RESTAURANDO...")
        print(f"   1. Salvando banco atual como: {backup_current}")
        shutil.copy2('gymnight.db', backup_current)
        
        print(f"   2. Restaurando do backup...")
        shutil.copy2('gymnight.db.backup', 'gymnight.db')
        
        print(f"\n✅ RESTAURAÇÃO CONCLUÍDA!")
        print(f"   Seu banco de dados foi restaurado do backup.")
        print(f"   O banco anterior foi salvo em: {backup_current}")
    else:
        print(f"\n✅ Banco atual está OK (tem {total_current} registros)")
        print(f"   Backup tem {total_backup} registros")
        if total_current >= total_backup:
            print(f"   Não é necessário restaurar.")

elif backup_data and not current_data:
    print("⚠️  Banco atual com problemas, mas backup está OK!")
    print("🔄 Restaurando do backup...")
    shutil.copy2('gymnight.db.backup', 'gymnight.db')
    print("✅ RESTAURAÇÃO CONCLUÍDA!")

print("\n" + "=" * 60)
