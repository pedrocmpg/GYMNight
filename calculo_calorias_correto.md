# Análise do Cálculo de Calorias - GYMNight

## ❌ PROBLEMA IDENTIFICADO

### Código Atual (INCORRETO)
```python
# ui/screens/dashboard.py, linha 310
calorias = int(vol * 5)
```

**O que está fazendo:**
- Multiplica o volume total (peso × reps) por 5
- Exemplo: 1000 kg de volume = 5000 kcal

**Por que está errado:**
1. Não usa a fórmula MET científica
2. Não considera o tipo de exercício (cada um tem MET diferente)
3. Não considera o peso corporal do usuário
4. Não considera o tempo de execução
5. O valor resultante é completamente arbitrário

---

## ✅ FÓRMULA CORRETA (do documento)

```
Calorias = (MET × Peso_kg × Tempo_min) / 60
```

### Parâmetros:
- **MET**: Varia por exercício (2.8 a 11.0)
- **Peso_kg**: Peso corporal do usuário
- **Tempo_min**: 4 segundos por repetição = 0.0667 min/rep

### Exemplo de Cálculo Correto:

**Supino Reto (MET 6.0) - Usuário 70kg:**
- 3 séries × 10 reps = 30 reps
- Tempo total: 30 × 4 seg = 120 seg = 2 min
- Calorias = (6.0 × 70 × 2) / 60 = **14 kcal**

**Ou por repetição:**
- Calorias/rep = (6.0 × 70 × 0.0667) / 60 = **0.47 kcal**
- 30 reps × 0.47 = **14.1 kcal**

---

## 📊 COMPARAÇÃO

### Exemplo: Treino com 1000 kg de volume total

**Código Atual (ERRADO):**
```
1000 kg × 5 = 5000 kcal ❌
```

**Cálculo Correto (exemplo realista):**
```
Supino: 10 séries × 10 reps = 100 reps × 0.47 kcal = 47 kcal
Agachamento: 10 séries × 10 reps = 100 reps × 0.39 kcal = 39 kcal
Rosca: 10 séries × 10 reps = 100 reps × 0.27 kcal = 27 kcal
Total: ~113 kcal ✓
```

**Diferença:** O código atual está superestimando em **~44x** (4400%)!

---

## 🔧 SOLUÇÃO NECESSÁRIA

Para corrigir, o sistema precisa:

1. **Criar tabela de METs no banco de dados**
   ```sql
   CREATE TABLE exercise_met_values (
       exercise_id INTEGER PRIMARY KEY,
       met_value REAL NOT NULL
   );
   ```

2. **Calcular calorias por série**
   ```python
   def calculate_calories(exercise_id, reps, user_weight_kg):
       met = get_met_value(exercise_id)
       time_min = reps * 4 / 60  # 4 seg/rep
       calories = (met * user_weight_kg * time_min) / 60
       return calories
   ```

3. **Somar todas as séries do treino**
   ```python
   total_calories = sum(
       calculate_calories(log.exercise_id, log.reps, user_weight)
       for log in workout_logs
   )
   ```

---

## 📝 CONCLUSÃO

**Status do cálculo atual:** ❌ **INCORRETO**

**Problemas:**
- Fórmula arbitrária sem base científica
- Valores superestimados em ~4400%
- Não segue o documento `gasto_calorico_exercicio.md`

**Recomendação:** Implementar a fórmula MET correta conforme documentado.
