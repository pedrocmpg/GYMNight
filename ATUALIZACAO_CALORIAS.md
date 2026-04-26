# Atualização do Cálculo de Calorias - GYMNight

## ✅ Correções Implementadas

### 1. Fórmula MET Correta
O sistema agora usa a fórmula científica baseada em MET (Metabolic Equivalent of Task):

```
Calorias = (MET × Peso_kg × Tempo_min) / 60
```

**Parâmetros:**
- **MET**: Valor específico por exercício (2.8 a 11.0)
- **Peso_kg**: Peso corporal do usuário
- **Tempo_min**: 4 segundos por repetição = 0.0667 min/rep

### 2. Banco de Dados Atualizado

**Nova tabela criada:**
```sql
CREATE TABLE exercise_met_values (
    exercise_id INTEGER PRIMARY KEY,
    met_value   REAL NOT NULL
);
```

**Valores MET por categoria:**
- Exercícios de peito (supino, flexão): 6.0 - 7.5
- Exercícios de costas (remada, barra): 5.0 - 7.5
- Exercícios de ombros: 3.5 - 7.5
- Exercícios de bíceps/tríceps: 3.5
- Exercícios de pernas (agachamento): 3.5 - 5.0
- Exercícios de abdômen: 2.8 - 3.8
- Exercícios explosivos (mountain climbers): 11.0

### 3. Dashboard Atualizado

O card "Calorias queimadas" agora:
- ✅ Usa a fórmula MET correta
- ✅ Considera o peso do usuário (de user_data.json)
- ✅ Calcula baseado no tempo de execução (4 seg/rep)
- ✅ Soma apenas séries normais (exclui aquecimento)
- ✅ Mostra valores realistas (~100-300 kcal por treino)

### 4. Engine Atualizado

Nova função adicionada em `RoutineManager`:
```python
def calculate_session_calories(session_id: int, user_weight_kg: float = 70.0) -> float
```

---

## 🚀 Como Aplicar a Atualização

### Passo 1: Fechar o Aplicativo
Certifique-se de que o GYMNight está **completamente fechado** antes de continuar.

### Passo 2: Executar o Script de Migração
```bash
python populate_met_values.py
```

Este script irá:
1. Criar a tabela `exercise_met_values` (se não existir)
2. Popular com valores MET de todos os exercícios cadastrados
3. Usar valor padrão (5.0) para exercícios sem MET específico

**Saída esperada:**
```
Populando valores MET...
✓ supino reto (barra): MET 6.0
✓ agachamento livre (back squat): MET 5.0
✓ rosca direta (barra): MET 3.5
...
✅ Concluído!
   - 150 exercícios com MET específico
   - 5 exercícios com MET padrão (5.0)
```

### Passo 3: Reiniciar o Aplicativo
Abra o GYMNight normalmente. O dashboard agora mostrará valores corretos de calorias.

---

## 📊 Comparação Antes vs Depois

### Exemplo: Treino de Peito (1000 kg volume total)

**ANTES (INCORRETO):**
```
1000 kg × 5 = 5000 kcal ❌
```

**DEPOIS (CORRETO):**
```
Supino: 30 reps × 0.47 kcal = 14 kcal
Crucifixo: 30 reps × 0.47 kcal = 14 kcal
Flexão: 50 reps × 0.58 kcal = 29 kcal
Total: ~57 kcal ✓
```

### Valores Realistas por Tipo de Treino

| Tipo de Treino | Calorias Estimadas |
|----------------|-------------------|
| Treino de Peito/Costas | 80-150 kcal |
| Treino de Pernas | 100-200 kcal |
| Treino de Braços | 50-100 kcal |
| Treino Full Body | 150-300 kcal |

---

## 🔍 Verificação

Para verificar se a atualização funcionou:

1. Abra o GYMNight
2. Vá para o Dashboard
3. Verifique o card "Calorias queimadas"
4. O valor deve estar entre 0-500 kcal (valores realistas)
5. Se ainda mostrar milhares de kcal, execute novamente o script

---

## 📚 Referências

- Documento base: `gasto_calorico_exercicio.md`
- Fórmula MET: 2024 Adult Compendium of Physical Activities
- Tempo por repetição: 4 segundos (padrão da literatura)
- Peso de referência: 70 kg (ajustável por usuário)

---

## ⚠️ Notas Importantes

1. **Séries de aquecimento não contam**: Apenas séries normais (set_type='N') são incluídas no cálculo
2. **Peso do usuário**: O sistema busca o peso de `user_data.json`. Se não encontrar, usa 70kg como padrão
3. **Exercícios novos**: Exercícios criados após esta atualização receberão MET automaticamente se estiverem no mapa
4. **Valores conservadores**: Para exercícios sem MET específico, usa-se 5.0 (valor médio conservador)

---

## 🐛 Solução de Problemas

### Erro: "database is locked"
**Solução:** Feche completamente o GYMNight e tente novamente.

### Valores ainda incorretos
**Solução:** 
1. Verifique se o script foi executado com sucesso
2. Reinicie o aplicativo
3. Execute: `python -c "from database import DatabaseConnection; db = DatabaseConnection(); print(db.fetchone('SELECT COUNT(*) as c FROM exercise_met_values'))"`

### MET não encontrado para exercício personalizado
**Solução:** O sistema usará MET 5.0 automaticamente. Para ajustar:
```sql
UPDATE exercise_met_values SET met_value = 6.0 WHERE exercise_id = X;
```
