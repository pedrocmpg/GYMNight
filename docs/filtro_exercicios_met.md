# Filtro de Exercícios com Cálculo de Calorias

## Resumo
Implementada funcionalidade de busca dinâmica com popup de exercícios que possuem valores MET parametrizados para cálculo de calorias.

## Mudanças Realizadas

### 1. EditRoutineWidget (`src/ui/screens/edit_routine_dialog.py`)

**Adicionado:**
- Checkbox "Mostrar apenas exercícios com cálculo de calorias" (ativado por padrão)
- Método `_get_exercises_with_met()` para buscar exercícios com valores MET
- Indicador visual 🔥 para exercícios que possuem MET parametrizado
- Filtro automático na busca quando checkbox está marcado
- **Popup dinâmico** que aparece conforme você digita

**Comportamento:**
- Ao digitar no campo de busca, popup aparece **automaticamente** abaixo
- Busca por **substring** (digitar "rem" encontra "remada", "remador", etc.)
- Apenas exercícios com valores MET são exibidos (se filtro ativo)
- Exercícios com MET recebem emoji 🔥 ao lado do nome
- Filtro pode ser desativado para mostrar todos os exercícios

### 2. ExerciseLineEdit (`src/ui/dialogs.py`)

**REFORMULADO COMPLETAMENTE:**
- ❌ Removido QCompleter (autocomplete nativo do Qt)
- ✅ Implementado popup manual com QListWidget
- ✅ Busca por substring em tempo real
- ✅ Popup aparece **automaticamente** conforme você digita
- ✅ Indicador visual 🔥 para exercícios com MET
- ✅ Filtro opcional por exercícios com MET

**Comportamento:**
- Popup aparece **abaixo do campo** conforme você digita
- Busca ignora acentos e maiúsculas/minúsculas
- Mostra até 20 resultados
- Clique no item para selecionar
- Popup fecha automaticamente ao perder foco

### 3. CreateWorkoutDialog (`src/ui/dialogs.py`)

**Adicionado:**
- Checkbox "Mostrar apenas exercícios com cálculo de calorias" (ativado por padrão)
- Método `_on_filter_changed()` para atualizar filtro dinamicamente
- Todos os campos de exercício usam o novo popup de busca

**Comportamento:**
- Ao criar novo treino, digitar no campo de exercício mostra popup com sugestões
- Por padrão, apenas exercícios com MET são sugeridos
- Usuário pode desmarcar checkbox para ver todos os exercícios
- Popup aparece **automaticamente** ao digitar

### 4. ActiveWorkoutScreen (`src/ui/screens/active_workout.py`)

**Adicionado:**
- Botão **"+ Exercício"** ao lado do botão "Carregar"
- Diálogo de busca com popup dinâmico
- Método `_add_exercise_dialog()` para abrir busca
- Método `_add_exercise_to_workout()` para adicionar exercício ao treino

**Comportamento:**
- Clique no botão "+ Exercício" abre diálogo de busca
- Digite parte do nome e popup aparece automaticamente
- Exercícios com MET aparecem primeiro (🔥)
- Clique no exercício para adicionar ao treino
- Exercício é adicionado com 4 séries padrão

## Benefícios

1. **Busca Dinâmica**: Popup aparece automaticamente conforme você digita
2. **Busca por Substring**: Não precisa digitar o nome completo
3. **Precisão no Cálculo de Calorias**: Foco em exercícios com cálculo preciso
4. **Experiência Melhorada**: Indicador visual claro (🔥) mostra quais exercícios têm MET
5. **Flexibilidade**: Filtro pode ser desativado quando necessário
6. **Consistência**: Implementado em todas as telas de seleção de exercícios

## Como Usar

### Criar Novo Treino
1. Clique em **"+ Novo Treino"**
2. No campo de exercício, digite parte do nome (ex: "rem")
3. **Popup aparece automaticamente** abaixo com sugestões
4. Clique no exercício desejado
5. Exercício é preenchido no campo

### Editar Treino
1. Edite um treino existente
2. No campo "Buscar exercício", digite parte do nome
3. **Popup aparece automaticamente** com sugestões
4. Clique no exercício para adicionar

### Treino Ativo
1. Durante o treino, clique em **"+ Exercício"**
2. Digite parte do nome no campo de busca
3. **Popup aparece automaticamente** com sugestões
4. Clique no exercício para adicionar ao treino

## Tabela de Referência

| Tela | Popup Automático | Filtro Padrão | Indicador Visual | Pode Desativar |
|------|------------------|---------------|------------------|----------------|
| Criar Treino | ✅ Sim | ✅ Ativo | 🔥 | ✅ Sim |
| Editar Treino | ✅ Sim | ✅ Ativo | 🔥 | ✅ Sim |
| Treino Ativo | ✅ Sim | ✅ Ativo | 🔥 | ❌ Não |

## Dados Técnicos

- **Tabela**: `exercise_met_values`
- **Coluna**: `exercise_id` (FK para `exercises.id`)
- **Query**: `SELECT exercise_id FROM exercise_met_values`
- **Indicador**: Emoji 🔥 (U+1F525)
- **Busca**: Substring case-insensitive sem acentos
- **Limite**: 20 resultados por busca
- **Popup**: QListWidget com Qt.ToolTip flag
