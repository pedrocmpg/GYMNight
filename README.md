# GYMNight 🏋️‍♂️🌙

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**GYMNight** é uma aplicação especializada de gerenciamento de treinos construída com Python e SQL. Projetada para fisiculturistas e entusiastas de fitness que desejam rastrear seu progresso com precisão, minimizando distrações durante as sessões de treino.

> 🎉 **Versão 2.0** - Projeto completamente reorganizado com estrutura profissional! Veja [CHANGELOG.md](CHANGELOG.md) para detalhes.

## 🎯 O Problema
A maioria dos aplicativos de fitness está repleta de recursos sociais e interfaces complexas que levam ao "scrolling no celular" entre as séries. **GYMNight** visa ser um "script de fundo" para seu treino: rápido, eficiente e orientado a dados.

## ✨ Funcionalidades Principais
* **Templates de Rotina Personalizados:** Crie e gerencie divisões de treino (Push/Pull/Legs, Upper/Lower, etc.).
* **Rastreamento de Volume e Intensidade:** Registre séries, repetições e peso com mínimo atrito.
* **Análise de Volume:** Cálculo automatizado de volume semanal por grupo muscular.
* **Orientado a Banco de Dados:** Persistência robusta de dados usando SQL para rastreamento histórico de progresso.
* **Dashboard de Saúde:** Visualização rápida de métricas como IMC e gasto calórico diário estimado.
* **Validação Inteligente:** O sistema impede a entrada de dados irreais usando validação rigorosa.

## 🛠️ Stack Tecnológica
* **Linguagem:** Python 3.12
* **Interface:** PySide6 (Qt for Python)
* **Banco de Dados:** SQLite
* **Arquitetura:** Lógica limpa e relacionamentos de dados eficientes

## 📊 Funcionalidades Detalhadas

### Gerenciamento de Treinos
- Criação de rotinas personalizadas
- Registro de exercícios, séries, repetições e cargas
- Tipos de série: Normal, Aquecimento, Dropset, Falha

### Análise de Performance
- Cálculo de volume por grupo muscular
- Análise de progressão histórica
- Métricas de performance em tempo real

### Cálculo de Calorias
- Baseado em valores MET (Metabolic Equivalent of Task)
- Fórmula: Calorias = (MET × Peso_kg × Tempo_min) / 60
- Tempo por repetição: 4 segundos


## 📧 Contato
Este é um projeto pessoal. Para dúvidas, consulte a documentação disponível.

---

**GYMNight** - Seu companheiro de treino orientado a dados 💪
