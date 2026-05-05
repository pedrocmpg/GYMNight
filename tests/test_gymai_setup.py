"""
test_gymai_setup.py
Script para verificar se o GymAI está configurado corretamente.
"""
import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv


def test_env_file():
    """Verifica se o arquivo .env existe."""
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ Arquivo .env não encontrado!")
        print("   Crie um arquivo .env na raiz do projeto com:")
        print("   GEMINI_API_KEY=sua_chave_aqui")
        return False
    print("✅ Arquivo .env encontrado")
    return True


def test_api_key():
    """Verifica se a API key está configurada."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ GEMINI_API_KEY não configurada no .env")
        print("   Adicione a linha: GEMINI_API_KEY=sua_chave_aqui")
        return False
    
    if api_key == "sua_chave_api_aqui":
        print("❌ GEMINI_API_KEY ainda está com valor de exemplo")
        print("   Substitua por sua chave real do Google AI Studio")
        return False
    
    if len(api_key) < 30:
        print("⚠️  GEMINI_API_KEY parece muito curta (pode estar incorreta)")
        return False
    
    print(f"✅ GEMINI_API_KEY configurada ({api_key[:10]}...)")
    return True


def test_library():
    """Verifica se a biblioteca google-genai está instalada."""
    try:
        from google import genai
        print("✅ Biblioteca google-genai instalada")
        return True
    except ImportError:
        print("❌ Biblioteca google-genai não instalada")
        print("   Execute: pip install google-genai")
        return False


def test_api_connection():
    """Testa a conexão com a API do Gemini."""
    try:
        from google import genai
        from google.genai import types
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key or api_key == "sua_chave_api_aqui":
            print("⏭️  Pulando teste de conexão (API key não configurada)")
            return True
        
        client = genai.Client(api_key=api_key)
        
        print("🔄 Testando conexão com a API...")
        response = client.models.generate_content(
            model='models/gemini-2.5-flash',
            contents='Responda apenas: OK'
        )
        
        if response.text:
            print("✅ Conexão com API do Gemini funcionando!")
            print(f"   Resposta de teste: {response.text[:50]}...")
            return True
        else:
            print("⚠️  API respondeu mas sem conteúdo")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao conectar com a API: {e}")
        return False


def main():
    """Executa todos os testes."""
    print("=" * 60)
    print("🤖 Verificação de Configuração do GymAI")
    print("=" * 60)
    print()
    
    results = []
    
    print("1. Verificando arquivo .env...")
    results.append(test_env_file())
    print()
    
    print("2. Verificando API key...")
    results.append(test_api_key())
    print()
    
    print("3. Verificando biblioteca...")
    results.append(test_library())
    print()
    
    print("4. Testando conexão com API...")
    results.append(test_api_connection())
    print()
    
    print("=" * 60)
    if all(results):
        print("✅ Tudo configurado corretamente! O GymAI está pronto para uso.")
    else:
        print("❌ Alguns problemas foram encontrados. Corrija-os antes de usar o GymAI.")
    print("=" * 60)


if __name__ == "__main__":
    main()
