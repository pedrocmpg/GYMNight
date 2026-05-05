"""
Script para listar modelos disponíveis na API do Gemini
"""
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY não configurada")
        exit(1)
    
    client = genai.Client(api_key=api_key)
    
    print("📋 Listando modelos disponíveis:\n")
    
    models = client.models.list()
    for model in models:
        print(f"✅ {model.name}")
        if hasattr(model, 'supported_generation_methods'):
            print(f"   Métodos: {model.supported_generation_methods}")
        print()
    
except Exception as e:
    print(f"❌ Erro: {e}")
