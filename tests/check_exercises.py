#!/usr/bin/env python3
"""Script para verificar exercícios no banco de dados"""

from database import DatabaseConnection

db = DatabaseConnection()

print("=== EXERCÍCIOS NO BANCO ===")
exs = db.fetchall("SELECT id, canonical_name FROM exercises LIMIT 10")
total_exs = db.fetchall("SELECT id FROM exercises")
print(f"Total de exercícios: {len(total_exs)}\n")

for e in exs:
    print(f"{e['id']}: {e['canonical_name']}")

print("\n=== EXERCÍCIOS COM MET ===")
mets = db.fetchall("""
    SELECT e.id, e.canonical_name, m.met_value 
    FROM exercises e 
    JOIN exercise_met_values m ON e.id = m.exercise_id 
    LIMIT 10
""")
total_mets = db.fetchall("SELECT exercise_id FROM exercise_met_values")
print(f"Total com MET: {len(total_mets)}\n")

for m in mets:
    print(f"{m['id']}: {m['canonical_name']} (MET: {m['met_value']})")

print("\n=== BUSCA POR 'REM' ===")
search = "rem"
search_results = db.fetchall("""
    SELECT e.id, e.canonical_name 
    FROM exercises e 
    WHERE LOWER(e.canonical_name) LIKE ?
    LIMIT 10
""", (f"%{search}%",))
print(f"Resultados para '{search}': {len(search_results)}\n")

for r in search_results:
    print(f"{r['id']}: {r['canonical_name']}")

db.close()
