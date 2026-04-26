"""
Script para popular valores MET no banco de dados existente.
Executa uma vez para adicionar os valores MET aos exercícios já cadastrados.
"""

import time
from database import DatabaseConnection, _EXERCISE_MET_MAP, _normalize

def populate_met_values():
    """Popula a tabela exercise_met_values com os valores do mapa."""
    print("Aguardando liberação do banco de dados...")
    time.sleep(2)
    
    db = DatabaseConnection()
    
    print("Populando valores MET...")
    
    # Busca todos os exercícios
    exercises = db.fetchall("SELECT id, canonical_name FROM exercises")
    
    updated = 0
    not_found = 0
    
    for exercise in exercises:
        exercise_id = exercise["id"]
        canonical_name = exercise["canonical_name"]
        
        # Busca o valor MET no mapa
        met_value = _EXERCISE_MET_MAP.get(canonical_name)
        
        if met_value:
            # Insere ou atualiza o valor MET
            db.execute_write(
                "INSERT OR REPLACE INTO exercise_met_values (exercise_id, met_value) VALUES (?, ?)",
                (exercise_id, met_value),
            )
            updated += 1
            print(f"✓ {canonical_name}: MET {met_value}")
        else:
            not_found += 1
            print(f"⚠ {canonical_name}: MET não encontrado (usando padrão 5.0)")
            # Insere valor padrão conservador
            db.execute_write(
                "INSERT OR IGNORE INTO exercise_met_values (exercise_id, met_value) VALUES (?, ?)",
                (exercise_id, 5.0),
            )
    
    print(f"\n✅ Concluído!")
    print(f"   - {updated} exercícios com MET específico")
    print(f"   - {not_found} exercícios com MET padrão (5.0)")
    
    db.close()

if __name__ == "__main__":
    populate_met_values()
