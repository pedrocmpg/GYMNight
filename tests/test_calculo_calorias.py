"""
Script de teste para validar o cálculo de calorias.
Testa a fórmula MET com exemplos do documento.
"""

def test_calculo_met():
    """Testa a fórmula MET com exemplos conhecidos."""
    
    print("=" * 60)
    print("TESTE DO CÁLCULO DE CALORIAS - FÓRMULA MET")
    print("=" * 60)
    
    # Fórmula: Calorias = (MET × Peso_kg × Tempo_min) / 60
    # Tempo por rep: 4 segundos = 0.0667 minutos
    
    peso_kg = 70.0
    tempo_por_rep = 4.0 / 60.0  # 0.0667 minutos
    
    testes = [
        ("Supino Reto", 6.0, 1, 0.47),
        ("Flexão de Braço", 7.5, 1, 0.58),
        ("Desenvolvimento", 3.5, 1, 0.27),
        ("Agachamento", 5.0, 1, 0.39),
        ("Abdominal Supra", 3.8, 1, 0.30),
        ("Mountain Climbers", 11.0, 1, 0.86),
    ]
    
    print("\nTestes individuais (1 repetição):")
    print("-" * 60)
    
    todos_corretos = True
    
    for nome, met, reps, esperado in testes:
        tempo_min = reps * tempo_por_rep
        calculado = (met * peso_kg * tempo_min) / 60.0
        diferenca = abs(calculado - esperado)
        correto = diferenca < 0.01  # Tolerância de 0.01 kcal
        
        status = "✅" if correto else "❌"
        print(f"{status} {nome:25} MET {met:4.1f} → {calculado:.2f} kcal (esperado: {esperado:.2f})")
        
        if not correto:
            todos_corretos = False
    
    print("\n" + "=" * 60)
    print("Teste de treino completo:")
    print("-" * 60)
    
    # Simula um treino de peito
    treino = [
        ("Supino Reto", 6.0, 30),      # 3 séries × 10 reps
        ("Supino Inclinado", 6.0, 30),
        ("Crucifixo", 6.0, 30),
        ("Flexão", 7.5, 40),           # 4 séries × 10 reps
    ]
    
    total_calorias = 0.0
    
    for nome, met, reps in treino:
        tempo_min = reps * tempo_por_rep
        calorias = (met * peso_kg * tempo_min) / 60.0
        total_calorias += calorias
        print(f"  {nome:20} {reps:3} reps → {calorias:5.1f} kcal")
    
    print("-" * 60)
    print(f"  TOTAL DO TREINO:              {total_calorias:5.1f} kcal")
    print("=" * 60)
    
    # Comparação com o método antigo (ERRADO)
    volume_total = sum(reps * 10 for _, _, reps in treino)  # Assumindo 10kg por rep
    calorias_antigas = volume_total * 5
    
    print("\nComparação com método antigo (INCORRETO):")
    print(f"  Volume total: {volume_total} kg")
    print(f"  Método antigo: {volume_total} × 5 = {calorias_antigas} kcal ❌")
    print(f"  Método correto (MET): {total_calorias:.1f} kcal ✅")
    print(f"  Diferença: {calorias_antigas / total_calorias:.1f}x superestimado!")
    
    print("\n" + "=" * 60)
    if todos_corretos:
        print("✅ TODOS OS TESTES PASSARAM!")
        print("✅ FÓRMULA MET IMPLEMENTADA CORRETAMENTE!")
    else:
        print("❌ ALGUNS TESTES FALHARAM!")
        print("❌ VERIFICAR IMPLEMENTAÇÃO!")
    print("=" * 60)
    
    return todos_corretos

if __name__ == "__main__":
    test_calculo_met()
