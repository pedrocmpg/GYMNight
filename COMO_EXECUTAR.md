# Como Executar o GYMNight

## 🐧 Seu Fluxo de Trabalho (WSL com Python Linux)

### Método 1: Script Automático (Recomendado)

```bash
cd ~/Projetos/GYMNight
./run.sh
```

### Método 2: Manual (Seu método atual)

```bash
cd ~/Projetos/GYMNight
source .venv/bin/activate
export DISPLAY=:0
export QT_QPA_PLATFORM=xcb
python main.py
```

### Método 3: Comando Único

```bash
cd ~/Projetos/GYMNight && source .venv/bin/activate && python main.py
```

> **Nota:** As variáveis `DISPLAY` e `QT_QPA_PLATFORM` já devem estar configuradas no seu ambiente.

## ⚙️ Configuração Permanente (Opcional)

Para não precisar exportar as variáveis toda vez, adicione ao seu `~/.bashrc`:

```bash
# Adicione estas linhas ao final do arquivo ~/.bashrc
export DISPLAY=:0
export QT_QPA_PLATFORM=xcb
```

Depois execute:
```bash
source ~/.bashrc
```

## 🔧 Solução de Problemas

### ❌ Erro: "Could not parse stylesheet"

**Isso é normal!** São apenas avisos do Qt. A interface gráfica funciona normalmente.

### ❌ Erro: "cannot connect to X server"

**Solução:**
```bash
export DISPLAY=:0
```

Ou verifique se você tem um servidor X rodando (WSLg ou VcXsrv).

### ❌ Erro: "qt.qpa.plugin: Could not load the Qt platform plugin"

**Solução:**
```bash
export QT_QPA_PLATFORM=xcb
```

### ❌ Erro: NumPy incompatível

**Solução:**
```bash
source .venv/bin/activate
pip install "numpy<2" --force-reinstall
```

## 📝 Primeira Execução

Na primeira vez que você executar o aplicativo após deletar os arquivos:

1. O banco de dados `gymnight.db` será recriado automaticamente
2. Você verá a tela de **Setup Inicial**
3. Preencha seus dados:
   - Nome
   - Peso (kg)
   - Altura (cm)
   - Gênero
   - Objetivo
   - Frequência de treino
4. Clique em **"Começar"**
5. Pronto! Você está no dashboard

## 🚀 Atalho Rápido

Crie um alias no seu `~/.bashrc` para facilitar:

```bash
# Adicione ao ~/.bashrc
alias gymnight='cd ~/Projetos/GYMNight && source .venv/bin/activate && python main.py'
```

Depois é só executar:
```bash
gymnight
```

## 📊 Verificar se está funcionando

Se você ver estes avisos, está tudo OK:
```
Could not parse stylesheet of object QLineEdit
Could not parse stylesheet of object QDoubleSpinBox
Could not parse stylesheet of object QSpinBox
```

A interface gráfica deve abrir normalmente! 💪

## 🎯 Resumo

**Seu comando atual funciona perfeitamente:**
```bash
cd Projetos/GYMNight
source .venv/bin/activate
python main.py
```

**Apenas certifique-se de que estas variáveis estejam configuradas:**
- `DISPLAY=:0` (já está configurado no seu sistema)
- `QT_QPA_PLATFORM=xcb` (opcional, mas recomendado)

---

**Tudo funcionando! Bons treinos! 🏋️‍♂️**
