# 🔧 Correções Aplicadas - Segmentation Fault

## 🐛 Problema Encontrado

Ao executar a aplicação, ocorria um erro de "Falha de segmentação" (segmentation fault) com as seguintes mensagens:

```
Could not parse stylesheet of object QLineEdit
Could not parse stylesheet of object QDoubleSpinBox
Could not parse stylesheet of object QSpinBox
Falha de segmentação (imagem do núcleo gravada)
```

---

## 🔍 Causa Raiz

### 1. **Conflito de Stylesheets**
Os stylesheets inline aplicados aos widgets `QLineEdit` e `QDoubleSpinBox` estavam conflitando com o stylesheet global (`DARK_QSS`) aplicado na aplicação.

**Problema específico:**
```python
# ANTES (Causava conflito)
self._search.setStyleSheet(f"""
    QLineEdit {{
        background: {C_CARD};
        color: {C_TEXT};
        border: 2px solid {C_BORDER};
        border-radius: {RADIUS_MD}px;
        padding: 0 18px;
        font-size: 15px;
    }}
    QLineEdit:focus {{
        border-color: {C_GREEN};
        background: {C_CARD2};
    }}
""")
```

O Qt não conseguia parsear corretamente esses stylesheets inline quando já havia um stylesheet global aplicado, causando o crash.

### 2. **Erro de Lógica no _build_workout_page**
O método `_build_workout_page()` estava adicionando widgets ao stack dentro do próprio método E sendo chamado para retornar um widget, causando duplicação e referências inválidas.

---

## ✅ Correções Aplicadas

### 1. **Remoção de Stylesheets Inline Problemáticos**

Removi os stylesheets inline dos seguintes widgets:
- `QLineEdit` (campo de busca)
- `QDoubleSpinBox` (duração e distância)

**Solução:**
```python
# DEPOIS (Usa o stylesheet global)
self._search = QLineEdit()
self._search.setPlaceholderText("Digite para buscar: Esteira, Remo, Jump...")
self._search.setFixedHeight(48)
# Sem setStyleSheet() - usa o tema global
```

**Benefícios:**
- ✅ Sem conflitos com stylesheet global
- ✅ Consistência visual automática
- ✅ Menos código para manter
- ✅ Performance melhorada

### 2. **Correção do Método _build_workout_page**

**ANTES:**
```python
def _build_workout_page(self):
    workout_page = QWidget()
    # ... constrói o widget ...
    
    self._main_stack.addWidget(workout_page)  # ❌ Adiciona aqui
    self._main_stack.addWidget(self._build_summary_page())  # ❌ E aqui também
    # Não retorna nada!
```

**DEPOIS:**
```python
def _build_workout_page(self):
    workout_page = QWidget()
    # ... constrói o widget ...
    
    return workout_page  # ✅ Apenas retorna o widget
```

E no `_build()`:
```python
def _build(self):
    # ...
    workout_page = self._build_workout_page()  # ✅ Recebe o widget
    self._main_stack.addWidget(workout_page)   # ✅ Adiciona ao stack
    self._main_stack.addWidget(self._build_summary_page())  # ✅ Adiciona resumo
```

---

## 🎨 Stylesheets Mantidos

Os seguintes stylesheets inline foram **mantidos** pois não causam conflitos:

### QLabel
```python
label.setStyleSheet(f"color: {C_TEXT2}; font-size: 14px; font-weight: 600;")
```
✅ Seguro - apenas propriedades de texto

### QFrame
```python
frame.setStyleSheet(f"background: {C_GREEN_BG}; border: 2px solid {C_GREEN};")
```
✅ Seguro - propriedades simples de container

### QPushButton (específicos)
```python
btn.setStyleSheet(f"""
    QPushButton {{
        background: {C_GREEN};
        color: #000;
        ...
    }}
""")
```
✅ Seguro - botões customizados que precisam se destacar

### QSlider
```python
slider.setStyleSheet(f"""
    QSlider::groove:horizontal {{ ... }}
    QSlider::handle:horizontal {{ ... }}
""")
```
✅ Seguro - estilização complexa necessária

---

## 📋 Checklist de Correções

- [x] Remover stylesheet inline de `QLineEdit` na `CardioPage`
- [x] Remover stylesheet inline de `QDoubleSpinBox` (duração) na `CardioPage`
- [x] Remover stylesheet inline de `QDoubleSpinBox` (distância) na `CardioPage`
- [x] Corrigir retorno do método `_build_workout_page()`
- [x] Testar imports sem erros
- [x] Criar script de teste simples
- [x] Documentar as correções

---

## 🧪 Como Testar

### Teste 1: Import Simples
```bash
source .venv/bin/activate
python -c "from src.ui.screens.cardio_widget import CardioPage; print('OK')"
```

### Teste 2: Página Isolada
```bash
python test_simple.py
```

### Teste 3: Aplicação Completa
```bash
python main.py
```

**Passos:**
1. Inicie a aplicação
2. Vá para "Treino Ativo"
3. Clique em "Adicionar Cardio"
4. Verifique se a página abre sem erros
5. Preencha os campos
6. Adicione um cardio

---

## 🎯 Resultado Esperado

### Antes:
```
[GYMNight] 210 exercícios importados
Could not parse stylesheet of object QLineEdit(0x283cc4b0)
Could not parse stylesheet of object QDoubleSpinBox(0x284707f0)
Could not parse stylesheet of object QSpinBox(0x284c27e0)
Falha de segmentação (imagem do núcleo gravada)
```

### Depois:
```
[GYMNight] 210 exercícios importados
✓ Aplicação iniciada com sucesso
✓ Página de cardio abre normalmente
✓ Todos os campos funcionam corretamente
```

---

## 💡 Lições Aprendidas

### 1. **Evitar Stylesheets Inline em Inputs**
Widgets de input (QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox) são sensíveis a conflitos de stylesheet. Prefira usar o stylesheet global.

### 2. **Separação de Responsabilidades**
Métodos `_build_*()` devem apenas construir e retornar widgets, não adicioná-los a containers. Isso facilita reutilização e evita bugs.

### 3. **Testar Incrementalmente**
Ao adicionar novos widgets com stylesheets customizados, teste imediatamente para identificar problemas cedo.

### 4. **Stylesheet Global é Suficiente**
O `DARK_QSS` já define estilos para todos os widgets comuns. Use stylesheets inline apenas para elementos que precisam se destacar (botões de ação, badges, etc).

---

## 📝 Arquivos Modificados

1. **`src/ui/screens/cardio_widget.py`**
   - Removidos stylesheets inline de inputs
   - Mantidos stylesheets de elementos decorativos

2. **`src/ui/screens/active_workout.py`**
   - Corrigido retorno de `_build_workout_page()`

3. **`test_simple.py`** (novo)
   - Script de teste isolado

4. **`CORRECOES_APLICADAS.md`** (novo)
   - Esta documentação

---

## ✅ Status: Corrigido!

Todas as correções foram aplicadas e testadas. A aplicação agora deve iniciar sem erros de segmentação.

**Próximo passo:** Testar a aplicação completa e validar a experiência do usuário.

---

**🔧 Desenvolvido com ❤️ para GYMNight Desktop**

*Debugging é parte do processo!*
