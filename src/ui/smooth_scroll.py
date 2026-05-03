"""
smooth_scroll.py
Implementa rolagem suave para QScrollArea no PySide6.
"""
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QObject, Property
from PySide6.QtWidgets import QScrollArea, QScrollBar


class SmoothScrollArea(QScrollArea):
    """QScrollArea com rolagem suave e otimizada."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animation = None
        self._setup_smooth_scroll()
    
    def _setup_smooth_scroll(self):
        """Configura a rolagem suave."""
        # Otimização: usa single step menor para rolagem mais suave
        v_bar = self.verticalScrollBar()
        if v_bar:
            v_bar.setSingleStep(20)  # Pixels por step (padrão é muito alto)
        
        h_bar = self.horizontalScrollBar()
        if h_bar:
            h_bar.setSingleStep(20)
    
    def wheelEvent(self, event):
        """Override do evento de rolagem para suavizar."""
        # Pega o delta do scroll (positivo = para cima, negativo = para baixo)
        delta = event.angleDelta().y()
        
        # Calcula o novo valor da scrollbar
        v_bar = self.verticalScrollBar()
        if not v_bar:
            return super().wheelEvent(event)
        
        # Multiplica por um fator menor para rolagem mais suave
        # Valor padrão do Qt é 120 por "click" do mouse wheel
        # Reduzimos para 40 pixels por click para suavidade
        step = -delta // 3  # Divide por 3 para suavizar
        
        new_value = v_bar.value() + step
        new_value = max(v_bar.minimum(), min(new_value, v_bar.maximum()))
        
        # Anima a transição
        if self._animation:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(v_bar, b"value")
        self._animation.setDuration(150)  # 150ms de animação
        self._animation.setStartValue(v_bar.value())
        self._animation.setEndValue(new_value)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.start()
        
        event.accept()


def apply_smooth_scroll(scroll_area: QScrollArea):
    """
    Aplica otimizações de rolagem suave a uma QScrollArea existente.
    
    Args:
        scroll_area: QScrollArea para otimizar
    """
    # Configura single step menor
    v_bar = scroll_area.verticalScrollBar()
    if v_bar:
        v_bar.setSingleStep(20)
    
    h_bar = scroll_area.horizontalScrollBar()
    if h_bar:
        h_bar.setSingleStep(20)
    
    # Instala event filter para suavizar wheel events
    scroll_area.installEventFilter(SmoothScrollFilter(scroll_area))


class SmoothScrollFilter(QObject):
    """Event filter para suavizar rolagem em QScrollArea."""
    
    def __init__(self, scroll_area: QScrollArea):
        super().__init__(scroll_area)
        self.scroll_area = scroll_area
        self._animation = None
    
    def eventFilter(self, obj, event):
        """Filtra eventos de wheel para suavizar."""
        from PySide6.QtCore import QEvent
        
        if event.type() == QEvent.Wheel and obj == self.scroll_area:
            delta = event.angleDelta().y()
            v_bar = self.scroll_area.verticalScrollBar()
            
            if v_bar:
                step = -delta // 3
                new_value = v_bar.value() + step
                new_value = max(v_bar.minimum(), min(new_value, v_bar.maximum()))
                
                if self._animation:
                    self._animation.stop()
                
                self._animation = QPropertyAnimation(v_bar, b"value")
                self._animation.setDuration(150)
                self._animation.setStartValue(v_bar.value())
                self._animation.setEndValue(new_value)
                self._animation.setEasingCurve(QEasingCurve.OutCubic)
                self._animation.start()
                
                return True  # Evento tratado
        
        return super().eventFilter(obj, event)
