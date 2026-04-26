# Guia Rápido - GYMNight

## ⚡ Início Rápido em 5 Minutos

### 1. Instalação (2 min)

```bash
# Clone e entre no diretório
git clone https://github.com/seu-usuario/gymnight.git
cd gymnight

# Crie ambiente virtual
python -m venv .venv

# Ative (escolha seu sistema)
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/Mac

# Instale dependências
pip install -r requirements.txt
```

### 2. Execute (30 seg)

```bash
python main.py
```

**Pronto!** A aplicação deve abrir.

---

## 📚 Primeiros Passos

### Criar Primeira Rotina

1. Abra a aplicação
2. Vá para "Rotinas"
3. Clique em "Nova Rotina"
4. Adicione exercícios
5. Salve

### Registrar Primeiro Treino

1. Selecione uma rotina
2. Clique em "Iniciar Treino"
3. Registre séries, peso e reps
4. Finalize o treino

### Ver Resultados

1. Vá para "Resultados"
2. Veja análise de volume
3. Confira progressão

---

## 🔧 Comandos Úteis

```bash
# Executar aplicação
python main.py

# Executar testes
python -m pytest tests/

# Ver cobertura
python -m pytest --cov=src tests/
```

---

## 📖 Documentação

### Essencial
- [README.md](README.md) - Documentação principal
- [STRUCTURE.md](STRUCTURE.md) - Estrutura do projeto

### Para Desenvolvedores
- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - Migração de código

### Referência
- [CHANGELOG.md](CHANGELOG.md) - Histórico
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Resumo visual

---

## 🆘 Problemas Comuns

### Erro: ModuleNotFoundError

**Problema:** `ModuleNotFoundError: No module named 'src'`

**Solução:**
```bash
# Certifique-se de estar no diretório raiz
cd /path/to/gymnight
python main.py
```

### Erro: PySide6 não encontrado

**Problema:** `ModuleNotFoundError: No module named 'PySide6'`

**Solução:**
```bash
pip install -r requirements.txt
```

### Erro: Banco de dados

**Problema:** Erro ao acessar banco de dados

**Solução:**
```bash
# Delete o banco e deixe recriar
rm gymnight.db
python main.py
```



---

## 💡 Dicas

### Performance
- Use SSD para melhor performance do SQLite
- Feche outros apps durante treino
- Mantenha banco de dados < 100MB

### Backup
```bash
# Backup do banco
cp gymnight.db gymnight.db.backup

# Backup de configuração
cp config/user_data.json config/user_data.json.backup
```

### Customização
- Edite `src/ui/theme.py` para mudar cores
- Edite `config/user_data.json` para dados do usuário
- Veja `docs/` para mais informações técnicas

---

## 🎯 Próximos Passos

1. ✅ Instalou e executou
2. ⏳ Crie sua primeira rotina
3. ⏳ Registre seu primeiro treino
4. ⏳ Veja seus resultados
5. ⏳ Explore funcionalidades avançadas

---

## 📞 Suporte

- 📖 **Docs:** Veja [README.md](README.md)
- 📚 **Mais Info:** Consulte a documentação em [docs/](docs/)

---

**Boa sorte com seus treinos! 💪**
