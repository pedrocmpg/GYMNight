"""
ui/screens/gym_ai.py
Tela GymAI: Chat com IA para tirar dúvidas sobre treinos usando Gemini.
"""
from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget, QTextEdit,
)

from src.ui.theme import (
    C_BG, C_BORDER, C_CARD, C_GREEN, C_TEXT, C_TEXT2, 
    RADIUS_LG, RADIUS_MD, neon_glow
)
from src.ui.smooth_scroll import apply_smooth_scroll
from loguru import logger
import qtawesome as qta


# ---------------------------------------------------------------------------
# Worker Thread para comunicação com Gemini
# ---------------------------------------------------------------------------

class GeminiWorker(QThread):
    """Thread worker para fazer requisições à API do Gemini."""
    
    response_ready = Signal(str)  # Emite a resposta da IA
    error_occurred = Signal(str)  # Emite mensagens de erro
    
    def __init__(self, api_key: str, parent=None):
        super().__init__(parent)
        self._api_key = api_key
        self._question = ""
        self._conversation_history = []
        
    def set_question(self, question: str):
        """Define a pergunta a ser enviada."""
        self._question = question
        
    def set_history(self, history: list):
        """Define o histórico da conversa."""
        self._conversation_history = history
    
    def run(self):
        """Executa a requisição à API do Gemini."""
        try:
            from google import genai
            from google.genai import types
            
            # Configura o cliente
            client = genai.Client(api_key=self._api_key)
            
            # Prompt de sistema para configurar o comportamento da IA
            system_instruction = """Você é um personal trainer experiente do aplicativo GYMNight, 
um app de treino de musculação e fitness. Você é motivador, técnico e sempre fornece 
informações baseadas em ciência do exercício. 

Suas características:
- Motivador e encorajador, mas realista
- Técnico quando necessário, explicando biomecânica e fisiologia
- Foca em segurança e forma correta dos exercícios
- Adapta respostas ao nível do usuário
- Sugere progressões e variações de exercícios
- Considera periodização e recuperação
- Usa linguagem acessível mas precisa

Sempre que possível, relacione suas respostas ao contexto do GYMNight e incentive 
o uso consistente do app para tracking de progresso."""
            
            # Monta o histórico da conversa
            contents = []
            for msg in self._conversation_history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part(text=msg["content"])]
                ))
            
            # Adiciona a pergunta atual
            contents.append(types.Content(
                role="user",
                parts=[types.Part(text=self._question)]
            ))
            
            # Lista de modelos para tentar (do mais rápido ao mais robusto)
            models_to_try = [
                'models/gemini-2.5-flash',
                'models/gemini-2.0-flash',
                'models/gemini-flash-latest'
            ]
            
            response = None
            last_error = None
            
            # Tenta cada modelo até conseguir uma resposta
            for model_name in models_to_try:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=0.7,
                        )
                    )
                    # Se chegou aqui, funcionou
                    break
                except Exception as e:
                    last_error = e
                    logger.warning(f"Modelo {model_name} falhou: {e}")
                    continue
            
            # Verifica se conseguiu resposta
            if response and response.text:
                self.response_ready.emit(response.text)
            elif last_error:
                # Se todos os modelos falharam, mostra o último erro
                error_msg = str(last_error)
                if "503" in error_msg or "high demand" in error_msg.lower():
                    self.error_occurred.emit(
                        "⚠️ A API do Gemini está com alta demanda no momento. "
                        "Tente novamente em alguns segundos."
                    )
                elif "429" in error_msg or "quota" in error_msg.lower():
                    self.error_occurred.emit(
                        "⚠️ Você atingiu o limite de requisições. "
                        "Aguarde alguns minutos antes de tentar novamente."
                    )
                else:
                    self.error_occurred.emit(f"Erro ao processar sua pergunta: {error_msg}")
            else:
                self.error_occurred.emit("A IA não retornou uma resposta válida.")
            
        except ImportError:
            self.error_occurred.emit(
                "Biblioteca google-genai não instalada. "
                "Execute: pip install google-genai"
            )
        except Exception as e:
            logger.error(f"Erro ao comunicar com Gemini: {e}")
            error_msg = str(e)
            if "503" in error_msg or "high demand" in error_msg.lower():
                self.error_occurred.emit(
                    "⚠️ A API do Gemini está com alta demanda no momento. "
                    "Tente novamente em alguns segundos."
                )
            else:
                self.error_occurred.emit(f"Erro ao processar sua pergunta: {error_msg}")


# ---------------------------------------------------------------------------
# Widgets de mensagem
# ---------------------------------------------------------------------------

class _MessageBubble(QFrame):
    """Bolha de mensagem estilizada com suporte a Markdown."""
    
    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        self._is_user = is_user
        
        # Estilo do balão
        if is_user:
            # Usuário: fundo verde neon, texto preto, alinhado à direita
            self.setStyleSheet(f"""
                QFrame {{
                    background: {C_GREEN};
                    border: none;
                    border-radius: 15px;
                    padding: 16px 20px;
                }}
            """)
        else:
            # IA: fundo escuro, borda lateral esquerda verde neon
            self.setStyleSheet(f"""
                QFrame {{
                    background: #1e1e1e;
                    border: none;
                    border-left: 3px solid {C_GREEN};
                    border-radius: 15px;
                    padding: 16px 20px;
                }}
            """)
        
        # Layout
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        
        # Widget de texto com suporte a Markdown
        if is_user:
            # Para mensagens do usuário, usa QLabel simples
            text_widget = QLabel(text)
            text_widget.setWordWrap(True)
            text_widget.setTextFormat(Qt.PlainText)
            text_widget.setStyleSheet(f"""
                color: #000000;
                font-size: 14px;
                background: transparent;
                border: none;
            """)
            lay.addWidget(text_widget)
        else:
            # Para mensagens da IA, usa QLabel com MarkdownText
            text_widget = QLabel(text)
            text_widget.setWordWrap(True)
            text_widget.setTextFormat(Qt.MarkdownText)
            text_widget.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
            text_widget.setStyleSheet(f"""
                QLabel {{
                    color: {C_TEXT};
                    font-size: 14px;
                    background: transparent;
                    border: none;
                }}
            """)
            lay.addWidget(text_widget)
        
        # Efeito neon sutil para mensagens do usuário
        if is_user:
            neon_glow(self, C_GREEN, blur=15, opacity=80)


class _MessageContainer(QWidget):
    """Container que alinha a mensagem à esquerda ou direita com largura máxima."""
    
    def __init__(self, bubble: _MessageBubble, is_user: bool, parent=None):
        super().__init__(parent)
        
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        
        # Define largura máxima da bolha (70% da largura disponível)
        bubble.setMaximumWidth(600)
        
        if is_user:
            lay.addStretch()
            lay.addWidget(bubble, 0, Qt.AlignRight)
        else:
            lay.addWidget(bubble, 0, Qt.AlignLeft)
            lay.addStretch()


# ---------------------------------------------------------------------------
# Tela principal GymAI
# ---------------------------------------------------------------------------

class GymAITab(QWidget):
    """Tela de chat com IA para dúvidas sobre treinos."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Carrega a API key do ambiente
        self._api_key = os.getenv("GEMINI_API_KEY", "")
        
        # Histórico da conversa
        self._conversation_history = []
        
        # Worker thread
        self._worker: Optional[GeminiWorker] = None
        
        self._build()
        
    def _build(self):
        """Constrói a interface."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        # Container principal
        container = QWidget()
        container.setStyleSheet(f"background: {C_BG};")
        container_lay = QVBoxLayout(container)
        container_lay.setContentsMargins(32, 32, 32, 32)
        container_lay.setSpacing(24)
        
        # Header
        header = QHBoxLayout()
        header.setSpacing(12)
        
        # Ícone de robô usando qtawesome
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon("fa5s.robot", color=C_GREEN).pixmap(32, 32))
        header.addWidget(icon_label)
        
        title = QLabel("GymAI")
        title.setStyleSheet(f"""
            color: {C_TEXT};
            font-size: 28px;
            font-weight: 800;
            background: transparent;
            border: none;
        """)
        header.addWidget(title)
        
        subtitle = QLabel("Seu personal trainer virtual")
        subtitle.setStyleSheet(f"""
            color: {C_TEXT2};
            font-size: 14px;
            background: transparent;
            border: none;
        """)
        subtitle.setAlignment(Qt.AlignBottom)
        header.addWidget(subtitle)
        header.addStretch()
        
        container_lay.addLayout(header)
        
        # Área de chat (scroll)
        chat_card = QFrame()
        chat_card.setStyleSheet(f"""
            QFrame {{
                background: {C_CARD};
                border: 2px solid {C_BORDER};
                border-radius: {RADIUS_LG}px;
            }}
        """)
        neon_glow(chat_card, C_GREEN, blur=20, opacity=60)
        
        chat_lay = QVBoxLayout(chat_card)
        chat_lay.setContentsMargins(0, 0, 0, 0)
        chat_lay.setSpacing(0)
        
        # Scroll area para mensagens
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        apply_smooth_scroll(self._scroll)
        
        # Container de mensagens
        self._messages_widget = QWidget()
        self._messages_widget.setStyleSheet("background: transparent;")
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setContentsMargins(24, 24, 24, 24)
        self._messages_layout.setSpacing(16)
        self._messages_layout.addStretch()
        
        self._scroll.setWidget(self._messages_widget)
        chat_lay.addWidget(self._scroll)
        
        container_lay.addWidget(chat_card, 1)
        
        # Input area
        input_card = QFrame()
        input_card.setStyleSheet(f"""
            QFrame {{
                background: {C_CARD};
                border: 2px solid {C_BORDER};
                border-radius: {RADIUS_LG}px;
            }}
        """)
        
        input_lay = QHBoxLayout(input_card)
        input_lay.setContentsMargins(16, 16, 16, 16)
        input_lay.setSpacing(12)
        
        # Campo de texto
        self._input_field = QLineEdit()
        self._input_field.setPlaceholderText("Digite sua pergunta sobre treinos...")
        self._input_field.setStyleSheet(f"""
            QLineEdit {{
                background: {C_BG};
                color: {C_TEXT};
                border: 2px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 12px 16px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {C_GREEN};
            }}
        """)
        self._input_field.returnPressed.connect(self._send_message)
        input_lay.addWidget(self._input_field, 1)
        
        # Botão enviar
        self._send_btn = QPushButton("Perguntar")
        self._send_btn.setFixedHeight(44)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_GREEN};
                color: #000000;
                border: none;
                border-radius: {RADIUS_MD}px;
                padding: 0 24px;
                font-weight: 700;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: #8ad900;
            }}
            QPushButton:disabled {{
                background: #3a3a3a;
                color: #6b7280;
            }}
        """)
        self._send_btn.clicked.connect(self._send_message)
        neon_glow(self._send_btn, C_GREEN, blur=30, opacity=150)
        input_lay.addWidget(self._send_btn)
        
        container_lay.addWidget(input_card)
        
        root.addWidget(container)
        
        # Mensagem de boas-vindas
        self._add_welcome_message()
    
    def _add_welcome_message(self):
        """Adiciona mensagem de boas-vindas."""
        welcome_text = """Olá! Sou o **GymAI**, seu personal trainer virtual do GYMNight!

Estou aqui para ajudar com:

• Dúvidas sobre exercícios e técnicas
• Sugestões de treinos e progressões
• Orientações sobre nutrição e recuperação
• Motivação e dicas de performance

Pode perguntar qualquer coisa sobre treino! 💪"""
        
        bubble = _MessageBubble(welcome_text, is_user=False)
        container = _MessageContainer(bubble, is_user=False)
        
        # Insere antes do stretch
        self._messages_layout.insertWidget(
            self._messages_layout.count() - 1, 
            container
        )
    
    def _send_message(self):
        """Envia a mensagem do usuário."""
        question = self._input_field.text().strip()
        
        if not question:
            return
        
        # Verifica se tem API key
        if not self._api_key:
            self._show_error("API Key do Gemini não configurada. Configure a variável de ambiente GEMINI_API_KEY.")
            return
        
        # Adiciona mensagem do usuário
        self._add_message(question, is_user=True)
        
        # Limpa o campo
        self._input_field.clear()
        
        # Desabilita input enquanto processa
        self._input_field.setEnabled(False)
        self._send_btn.setEnabled(False)
        self._send_btn.setText("Pensando...")
        
        # Adiciona ao histórico
        self._conversation_history.append({
            "role": "user",
            "content": question
        })
        
        # Cria e inicia o worker
        self._worker = GeminiWorker(self._api_key)
        self._worker.set_question(question)
        self._worker.set_history(self._conversation_history[:-1])  # Histórico sem a última mensagem
        self._worker.response_ready.connect(self._on_response)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()
    
    def _add_message(self, text: str, is_user: bool):
        """Adiciona uma mensagem ao chat."""
        bubble = _MessageBubble(text, is_user=is_user)
        container = _MessageContainer(bubble, is_user=is_user)
        
        # Insere antes do stretch
        self._messages_layout.insertWidget(
            self._messages_layout.count() - 1, 
            container
        )
        
        # Scroll para o final com delay para garantir que o widget foi renderizado
        QTimer.singleShot(100, self._scroll_to_bottom)
    
    def _scroll_to_bottom(self):
        """Faz scroll automático para o final da conversa."""
        scrollbar = self._scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _on_response(self, response: str):
        """Callback quando a resposta da IA chega."""
        # Adiciona ao histórico
        self._conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        # Adiciona mensagem da IA
        self._add_message(response, is_user=False)
    
    def _on_error(self, error_msg: str):
        """Callback quando ocorre um erro."""
        self._show_error(error_msg)
    
    def _show_error(self, error_msg: str):
        """Mostra uma mensagem de erro."""
        error_text = f"**⚠️ Erro:** {error_msg}"
        bubble = _MessageBubble(error_text, is_user=False)
        bubble.setStyleSheet(f"""
            QFrame {{
                background: #2a0a0a;
                border: none;
                border-left: 3px solid #ef4444;
                border-radius: 15px;
                padding: 16px 20px;
            }}
        """)
        container = _MessageContainer(bubble, is_user=False)
        
        self._messages_layout.insertWidget(
            self._messages_layout.count() - 1, 
            container
        )
        
        # Scroll para o final
        QTimer.singleShot(100, self._scroll_to_bottom)
    
    def _on_worker_finished(self):
        """Callback quando o worker termina."""
        # Reabilita input
        self._input_field.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._send_btn.setText("Perguntar")
        self._input_field.setFocus()
        
        # Limpa o worker
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
