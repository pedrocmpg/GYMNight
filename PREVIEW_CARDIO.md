# 🎨 Preview Visual - Tela de Cardio Melhorada

## 📱 Layout da Tela

```
┌─────────────────────────────────────────────────────────────┐
│  ✕  ADICIONAR CARDIO                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🏃 Registre sua atividade cardiovascular                   │
│  Escolha o tipo de cardio e registre suas métricas para    │
│  acompanhar seu progresso                                   │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  ⚡ ACESSO RÁPIDO                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                   │
│  │🏃 Corrida│ │🚴 Bicicleta│ │🏊 Natação│                  │
│  └──────────┘ └──────────┘ └──────────┘                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                   │
│  │🚶Caminhada│ │⛰️ Elíptico│ │🪜 Escada │                  │
│  └──────────┘ └──────────┘ └──────────┘                   │
│                                                             │
│  🔍 OU BUSQUE OUTRO TIPO                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Digite para buscar: Esteira, Remo, Jump...          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📊 Métricas do Treino                               │   │
│  │                                                     │   │
│  │ ⏱️ Duração *                                        │   │
│  │ ┌─────────────────────────────────────────────┐    │   │
│  │ │              30 min                         │    │   │
│  │ └─────────────────────────────────────────────┘    │   │
│  │                                                     │   │
│  │ 📏 Distância (opcional)                             │   │
│  │ ┌─────────────────────────────────────────────┐    │   │
│  │ │          Não informado                      │    │   │
│  │ └─────────────────────────────────────────────┘    │   │
│  │                                                     │   │
│  │ 💪 Intensidade (PSE)                          ┌──┐ │   │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│5 │ │   │
│  │ 😌 Leve    😊 Moderado    😤 Intenso    🔥 Máximo  │   │
│  │                                                     │   │
│  │ ┌─────────────────────────────────────────────┐    │   │
│  │ │ 🔥  Calorias Estimadas                      │    │   │
│  │ │     ~150 kcal                               │    │   │
│  │ └─────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────┐  ┌────────────────────────────────┐     │
│  │ ✕ Cancelar   │  │ ✓ Adicionar Cardio (GLOW)     │     │
│  └──────────────┘  └────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🎨 Elementos Visuais Destacados

### 1. Botões de Acesso Rápido
```
┌──────────────┐
│  🏃 Corrida  │  ← Hover: fundo verde, borda verde brilhante
└──────────────┘
```

### 2. Slider de Intensidade
```
💪 Intensidade (PSE)                                    ┌────┐
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│ 5  │
                                                        └────┘
                                                        ↑ Badge com glow
```

### 3. Card de Calorias
```
┌─────────────────────────────────────────────────────┐
│ 🔥  Calorias Estimadas                              │
│     ~150 kcal  ← Atualiza em tempo real             │
└─────────────────────────────────────────────────────┘
```

### 4. CardioRow (após adicionar)
```
┌─────────────────────────────────────────────────────────────┐
│ 🏃  Corrida                                    ┌────┐    ✕  │
│     ⏱️ 30 min  📏 5.0 km  💪 PSE 7/10         │150 │       │
│                                                │kcal│       │
│                                                └────┘       │
└─────────────────────────────────────────────────────────────┘
↑ Card com gradiente verde e glow neon
```

## 🎯 Interações

### Ao Clicar em Botão Rápido:
1. Campo de busca é preenchido automaticamente
2. Foco vai para o campo de duração
3. Usuário pode ajustar métricas rapidamente

### Ao Ajustar Duração ou PSE:
1. Calorias são recalculadas instantaneamente
2. Badge do PSE atualiza com animação suave
3. Feedback visual imediato

### Ao Adicionar Cardio:
1. Diálogo fecha com animação
2. CardioRow aparece na lista
3. Mostra todas as métricas + calorias
4. Efeito de glow destaca o novo item

## 🎨 Paleta de Cores Utilizada

```
Verde Neon:     #a2ff00  ━━━━━  Elementos principais
Verde Ativo:    #b5f542  ━━━━━  Hover states
Verde Escuro:   #1a2e0a  ━━━━━  Backgrounds
Texto Claro:    #ffffff  ━━━━━  Títulos
Texto Médio:    #6b7280  ━━━━━  Labels
Fundo Card:     #1a1a1a  ━━━━━  Cards
Borda:          #2a2a2a  ━━━━━  Separadores
```

## 📐 Dimensões e Espaçamento

```
Altura dos Inputs:     44px
Altura dos Botões:     48px (principais), 36px (secundários)
Raio de Borda:         10px (médio), 16px (grande)
Espaçamento Interno:   20px (cards), 16px (geral)
Espaçamento Entre:     16px (elementos), 8px (relacionados)
```

## ✨ Efeitos Especiais

### Glow Neon
- Aplicado em: Botão principal, badge PSE, CardioRow
- Cor: Verde (#a2ff00) com 50% opacidade
- Blur: 15-30px dependendo do elemento

### Gradientes
- CardioRow: Gradiente horizontal verde escuro
- Slider: Gradiente no preenchimento
- Hover: Transições suaves de cor

### Animações
- Hover: Escala 1.02x em botões
- Focus: Borda verde com transição 200ms
- Slider: Handle cresce ao hover

## 🔄 Estados Interativos

### Normal
```
┌──────────────┐
│  🏃 Corrida  │  Fundo: #1a1a1a, Borda: #2a2a2a
└──────────────┘
```

### Hover
```
┌──────────────┐
│  🏃 Corrida  │  Fundo: #1a3a00, Borda: #a2ff00 (GLOW)
└──────────────┘
```

### Selecionado
```
┌──────────────┐
│  🏃 Corrida  │  Fundo: #1a2e0a, Texto: #a2ff00
└──────────────┘
```

## 📱 Responsividade

- Largura mínima: 520px
- Botões rápidos: Grid 3 colunas
- Inputs: Largura 100% do container
- Espaçamento adapta-se ao tamanho

---

**🎨 Design System: GYMNight Neon Theme**
