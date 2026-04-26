# Changelog - GYMNight

## [2.0.0] - 2026-04-26

### 🎉 Reorganização Completa do Projeto

#### ✨ Adicionado

- **Nova estrutura de diretórios profissional**
  - `src/` - Todo código fonte organizado
  - `tests/` - Testes centralizados
  - `docs/` - Documentação organizada
  - `assets/` - Recursos (imagens, ícones)
  - `config/` - Arquivos de configuração

- **Modularização do código**
  - `src/core/` dividido em 4 módulos especializados:
    - `models.py` - Dataclasses de domínio
    - `normalization.py` - Engine de normalização
    - `performance.py` - Análise de performance
    - `routine.py` - Gerenciamento de rotinas
  
  - `src/database/` dividido em 3 módulos:
    - `connection.py` - Gerenciamento de conexão
    - `schema.py` - Definições de schema
    - `parser.py` - Parser e dados MET

- **Wrappers de compatibilidade**
  - `engine.py` - Mantém imports antigos funcionando
  - `database.py` - Mantém imports antigos funcionando
  - `models.py` - Mantém imports antigos funcionando

- **Documentação completa**
  - `README.md` - Documentação principal atualizada
  - `STRUCTURE.md` - Detalhes da estrutura
  - `MIGRATION_GUIDE.md` - Guia de migração
  - `CHANGELOG.md` - Este arquivo
  - `verify_structure.py` - Script de verificação

- **Melhorias no .gitignore**
  - Ignora arquivos de cache Python
  - Ignora ambientes virtuais
  - Ignora arquivos de IDE
  - Ignora banco de dados

#### 🔄 Modificado

- **engine.py**
  - Antes: Arquivo monolítico com 600+ linhas
  - Depois: Wrapper que re-exporta de `src/core/`
  - Código real dividido em 4 módulos especializados

- **database.py**
  - Antes: Arquivo com schema, parser e conexão misturados
  - Depois: Wrapper que re-exporta de `src/database/`
  - Código real dividido em 3 módulos especializados

- **models.py**
  - Antes: Modelos Qt na raiz
  - Depois: Wrapper que re-exporta de `src/ui_models/`

- **main.py**
  - Atualizado para importar de `src.ui`
  - Código mais limpo e organizado

- **Caminhos de ícones**
  - Antes: `icons/chest.png`
  - Depois: `assets/icons/chest.png`

#### 📁 Movido

- **Documentação**
  - `*.md` → `docs/*.md`
  - Exceto: README.md, STRUCTURE.md, MIGRATION_GUIDE.md, CHANGELOG.md

- **Testes**
  - `test_*.py` → `tests/test_*.py`

- **Configuração**
  - `user_data.json` → `config/user_data.json`

- **Utilitários**
  - `populate_met_values.py` → `src/utils/populate_met_values.py`
  - `check_runtime.py` → `src/utils/check_runtime.py`

- **UI**
  - `ui/` → `src/ui/` (mantendo estrutura interna)
  - `core/models.py` → `src/ui_models/models.py`

#### 🐛 Corrigido

- Imports circulares eliminados com modularização
- Estrutura confusa de `core/` (era modelos Qt, agora é lógica de negócio)
- Arquivos espalhados na raiz organizados em pastas apropriadas

#### 🔧 Técnico

- **Separação de responsabilidades**
  - Lógica de negócio (`src/core/`)
  - Acesso a dados (`src/database/`)
  - Interface (`src/ui/`)
  - Modelos Qt (`src/ui_models/`)

- **Testabilidade melhorada**
  - Módulos menores e mais focados
  - Dependências mais claras
  - Fácil mockar componentes

- **Manutenibilidade**
  - Arquivos menores (< 200 linhas)
  - Responsabilidade única
  - Código mais legível

#### 📊 Estatísticas

- **Antes:**
  - 3 arquivos grandes (600+ linhas cada)
  - 15+ arquivos .md na raiz
  - Estrutura confusa

- **Depois:**
  - 10+ módulos especializados (< 200 linhas cada)
  - Documentação organizada em `docs/`
  - Estrutura clara e profissional

#### ⚠️ Breaking Changes

**Nenhum!** Todos os imports antigos continuam funcionando através dos wrappers de compatibilidade.

#### 🔜 Próximos Passos

- [ ] Migrar imports para novos caminhos gradualmente
- [ ] Adicionar mais testes unitários
- [ ] Configurar CI/CD
- [ ] Adicionar type checking (mypy)
- [ ] Adicionar linting (pylint/flake8)
- [ ] Remover wrappers quando migração completa

#### 📝 Notas de Migração

Para migrar código existente, consulte `MIGRATION_GUIDE.md`.

Para entender a nova estrutura, consulte `STRUCTURE.md`.

Para verificar se tudo está OK, execute:
```bash
python verify_structure.py
```

---

## [1.0.0] - Anterior

### Versão Original

- Engine monolítico
- Database em arquivo único
- Estrutura básica
- Funcionalidades core implementadas

---

**Formato baseado em [Keep a Changelog](https://keepachangelog.com/)**
