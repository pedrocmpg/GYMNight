# 🎯 Instruções para Atualização do Cálculo de Calorias

## ⚠️ IMPORTANTE: Leia antes de usar

O cálculo de calorias foi **completamente corrigido** para usar a fórmula científica MET, conforme o documento `gasto_calorico_exercicio.md`.

---

## 🚀 Passo a Passo Simples

### 1️⃣ Feche o GYMNight
Certifique-se de que o aplicativo está **completamente fechado**.

### 2️⃣ Execute o Script de Atualização
Abra o terminal na pasta do projeto e execute:

```bash
python populate_met_values.py
```

**Você verá algo assim:**
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

### 3️⃣ Abra o GYMNight
Pronto! O cálculo de calorias agora está correto.

---

## 📊 O Que Mudou?

### ANTES (Errado):
```
Treino com 1000 kg de volume = 5000 kcal ❌
```

### DEPOIS (Correto):
```
Treino com 1000 kg de volume = ~100-150 kcal ✅
```

---

## ✅ Como Verificar se Funcionou

1. Abra o GYMNight
2. Vá para o **Dashboard**
3. Veja o card **"Calorias queimadas"**
4. O valor deve estar entre **0-500 kcal** (valores realistas)

**Se ainda mostrar milhares de kcal:**
- Feche o app completamente
- Execute novamente: `python populate_met_values.py`
- Reabra o app

---

## 🎓 Entenda os Valores

### Valores Normais por Tipo de Treino:

| Tipo de Treino | Calorias (pessoa 70kg) |
|----------------|------------------------|
| Braços (bíceps/tríceps) | 50-100 kcal |
| Peito ou Costas | 80-150 kcal |
| Pernas | 100-200 kcal |
| Full Body | 150-300 kcal |

**Nota:** Se você pesa mais ou menos que 70kg, os valores serão proporcionalmente diferentes.

---

## 🔧 Solução de Problemas

### ❌ Erro: "database is locked"
**Causa:** O GYMNight ainda está aberto.
**Solução:** Feche completamente o app e tente novamente.

### ❌ Valores ainda incorretos
**Solução:**
1. Verifique se o script foi executado com sucesso
2. Feche e reabra o GYMNight
3. Se persistir, delete o arquivo `gymnight.db` e reabra o app (⚠️ isso apagará seus dados!)

### ❌ Script não executa
**Causa:** Python não está instalado ou não está no PATH.
**Solução:** Certifique-se de ter Python 3.8+ instalado.

---

## 📚 Informações Técnicas

### Fórmula Usada:
```
Calorias = (MET × Peso_kg × Tempo_min) / 60
```

### Parâmetros:
- **MET**: Varia por exercício (ex: supino = 6.0, agachamento = 5.0)
- **Peso**: Seu peso corporal (lido de `user_data.json`, padrão 70kg)
- **Tempo**: 4 segundos por repetição (padrão científico)

### Exemplos:
```
Supino: 10 reps × 0.47 kcal/rep = 4.7 kcal
Agachamento: 10 reps × 0.39 kcal/rep = 3.9 kcal
Flexão: 10 reps × 0.58 kcal/rep = 5.8 kcal
```

---

## 🎉 Pronto!

Agora seu GYMNight calcula calorias de forma **cientificamente precisa**, seguindo o padrão internacional MET (Metabolic Equivalent of Task).

**Dúvidas?** Consulte os arquivos:
- `ATUALIZACAO_CALORIAS.md` - Guia técnico completo
- `RESUMO_CORRECAO_CALORIAS.md` - Resumo das mudanças
- `calculo_calorias_correto.md` - Análise detalhada

---

**Versão:** 2.0 - Cálculo MET Científico
**Data:** 2026-04-26
**Status:** ✅ TESTADO E VALIDADO
