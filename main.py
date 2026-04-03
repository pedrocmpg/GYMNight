"""
main.py - GYMNight
Interface gráfica principal: Dashboard de Rotinas → Treino Ativo.
"""

from __future__ import annotations

import sys
from typing import Any

from PySide6.QtCore import (
    QModelIndex,
    QObject,
    QSize,
    Qt,
    QThread,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from database import DatabaseConnection
from engine import (
    Exercise,
    NormalizationEngine,
    PerformanceAnalyzer,
    Routine,
    RoutineManager,
)
from models import (
    COL_EXERCISE,
    COL_REPS,
    COL_WEIGHT,
    SuggestionRole,
    WorkoutEntryModel,
)

# ---------------------------------------------------------------------------
# QSS – Dark Mode com detalhes em verde neon
# ---------------------------------------------------------------------------

DARK_QSS = """
QMainWindow, QWidget {
    background-color: #0d0d0d;
    color: #e0e0e0;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
}

QLabel#title {
    color: #39FF14;
    font-size: 22px;
    font-weight: bold;
    letter-spacing: 2px;
}

QLabel#subtitle {
    color: #888888;
    font-size: 11px;
    letter-spacing: 1px;
}

QLabel#stat {
    color: #39FF14;
    font-size: 15px;
    font-weight: bold;
}

QPushButton {
    background-color: #1a1a1a;
    color: #39FF14;
    border: 1px solid #39FF14;
    border-radius: 4px;
    padding: 8px 18px;
    font-weight: bold;
    letter-spacing: 1px;
}

QPushButton:hover {
    background-color: #39FF14;
    color: #0d0d0d;
}

QPushButton:pressed {
    background-color: #2acc10;
}

QPushButton#danger {
    color: #ff4444;
    border-color: #ff4444;
}

QPushButton#danger:hover {
    background-color: #ff4444;
    color: #0d0d0d;
}

QListWidget {
    background-color: #111111;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 4px;
}

QListWidget::item {
    padding: 12px 16px;
    border-bottom: 1px solid #1e1e1e;
    color: #cccccc;
}

QListWidget::item:selected {
    background-color: #1a2e1a;
    color: #39FF14;
    border-left: 3px solid #39FF14;
}

QListWidget::item:hover {
    background-color: #161616;
}

QTableView {
    background-color: #111111;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    gridline-color: #1e1e1e;
    selection-background-color: #1a2e1a;
    selection-color: #39FF14;
}

QHeaderView::section {
    background-color: #0d0d0d;
    color: #39FF14;
    border: none;
    border-bottom: 1px solid #39FF14;
    padding: 6px 10px;
    font-weight: bold;
    letter-spacing: 1px;
}

QLineEdit {
    background-color: #1a1a1a;
    color: #e0e0e0;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
    padding: 6px 10px;
}

QLineEdit:focus {
    border-color: #39FF14;
}

QScrollBar:vertical {
    background: #111111;
    width: 8px;
}

QScrollBar::handle:vertical {
    background: #39FF14;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""



# ---------------------------------------------------------------------------
# GhostValueDelegate – exibe SuggestionRole em cinza quando célula está vazia
# ---------------------------------------------------------------------------

class GhostValueDelegate(QStyledItemDelegate):
    """
    Delegate para colunas de Peso e Reps.
    Se a célula não tiver valor, renderiza o Ghost Value (última performance)
    em cinza claro como sugestão de meta.
    """

    GHOST_COLOR = QColor("#555555")

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        value = index.data(Qt.DisplayRole)

        # Célula com valor real → renderização padrão
        if value is not None:
            super().paint(painter, option, index)
            return

        # Busca ghost value via SuggestionRole
        suggestion = index.data(SuggestionRole)
        if suggestion is None:
            super().paint(painter, option, index)
            return

        col = index.column()
        if col == COL_WEIGHT:
            ghost_text = f"{suggestion.weight_kg:.1f} kg"
        elif col == COL_REPS:
            ghost_text = f"{suggestion.reps} reps"
        else:
            super().paint(painter, option, index)
            return

        # Desenha fundo de seleção se necessário
        self.initStyleOption(option, index)
        painter.save()

        if option.state & option.state.Selected:
            painter.fillRect(option.rect, QColor("#1a2e1a"))

        painter.setPen(self.GHOST_COLOR)
        font = painter.font()
        font.setItalic(True)
        painter.setFont(font)
        painter.drawText(
            option.rect.adjusted(6, 0, -6, 0),
            Qt.AlignVCenter | Qt.AlignLeft,
            ghost_text,
        )
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(100, 36)


# ---------------------------------------------------------------------------
# Diálogo: Criar Nova Rotina
# ---------------------------------------------------------------------------

class NewRoutineDialog(QDialog):
    """Diálogo simples para criar uma rotina com nome e exercícios."""

    def __init__(self, norm_engine: NormalizationEngine, parent=None) -> None:
        super().__init__(parent)
        self._norm = norm_engine
        self._exercise_ids: list[int] = []
        self._exercises: list[Exercise] = []
        self.setWindowTitle("Nova Rotina")
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Ex: Treino A – Peito e Tríceps")
        form.addRow("Nome da Rotina:", self._name_edit)
        layout.addLayout(form)

        # Campo de busca de exercício
        search_layout = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Buscar exercício (fuzzy)...")
        add_btn = QPushButton("Adicionar")
        add_btn.clicked.connect(self._add_exercise)
        search_layout.addWidget(self._search_edit)
        search_layout.addWidget(add_btn)
        layout.addLayout(search_layout)

        # Lista de exercícios adicionados
        self._list = QListWidget()
        self._list.setMaximumHeight(180)
        layout.addWidget(self._list)

        remove_btn = QPushButton("Remover Selecionado")
        remove_btn.setObjectName("danger")
        remove_btn.clicked.connect(self._remove_selected)
        layout.addWidget(remove_btn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_exercise(self) -> None:
        text = self._search_edit.text().strip()
        if not text:
            return

        matches = self._norm.resolve(text, threshold=0.5)
        if matches:
            ex = matches[0].exercise
        else:
            # Cria novo exercício com grupo muscular padrão (1 = Peito)
            ex = self._norm.get_or_create(text, muscle_group_id=1)

        if ex.id not in self._exercise_ids:
            self._exercise_ids.append(ex.id)
            self._exercises.append(ex)
            item = QListWidgetItem(f"{ex.canonical_name}  [{ex.muscle_group_name}]")
            item.setData(Qt.UserRole, ex.id)
            self._list.addItem(item)

        self._search_edit.clear()

    def _remove_selected(self) -> None:
        row = self._list.currentRow()
        if row >= 0:
            self._list.takeItem(row)
            self._exercise_ids.pop(row)
            self._exercises.pop(row)

    def routine_name(self) -> str:
        return self._name_edit.text().strip()

    def exercise_ids(self) -> list[int]:
        return list(self._exercise_ids)



# ---------------------------------------------------------------------------
# Tela 1: Dashboard de Rotinas
# ---------------------------------------------------------------------------

class DashboardScreen(QWidget):
    """Lista as rotinas disponíveis e permite iniciar um treino."""

    routine_selected = Signal(object, int)  # (Routine, session_id)

    def __init__(
        self,
        db: DatabaseConnection,
        routine_manager: RoutineManager,
        norm_engine: NormalizationEngine,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._rm = routine_manager
        self._norm = norm_engine
        self._build_ui()
        self._load_routines()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # Cabeçalho
        title = QLabel("⚡ GYMNIGHT")
        title.setObjectName("title")
        subtitle = QLabel("PERFORMANCE ENGINE  //  SELECT ROUTINE")
        subtitle.setObjectName("subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        # Lista de rotinas
        self._list = QListWidget()
        self._list.setAlternatingRowColors(False)
        layout.addWidget(self._list)

        # Botões
        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("▶  INICIAR TREINO")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._start_workout)

        new_btn = QPushButton("+  NOVA ROTINA")
        new_btn.clicked.connect(self._create_routine)

        btn_row.addWidget(new_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._start_btn)
        layout.addLayout(btn_row)

        self._list.itemSelectionChanged.connect(
            lambda: self._start_btn.setEnabled(bool(self._list.selectedItems()))
        )

    def _load_routines(self) -> None:
        self._list.clear()
        for routine in self._rm.list_routines():
            exercises = self._rm.get_routine_exercises(routine.id)
            label = f"{routine.name}   ({len(exercises)} exercícios)"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, routine)
            self._list.addItem(item)

    def _start_workout(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        routine: Routine = item.data(Qt.UserRole)

        # Cria nova sessão vinculada à rotina
        session_id = self._db.execute_write(
            "INSERT INTO workout_sessions (routine_id) VALUES (?)",
            (routine.id,),
        )
        self.routine_selected.emit(routine, session_id)

    def _create_routine(self) -> None:
        dlg = NewRoutineDialog(self._norm, parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        name = dlg.routine_name()
        ids  = dlg.exercise_ids()
        if not name or not ids:
            QMessageBox.warning(self, "Atenção", "Informe um nome e ao menos um exercício.")
            return
        self._rm.create_routine(name, ids)
        self._load_routines()


# ---------------------------------------------------------------------------
# Tela 2: Treino Ativo
# ---------------------------------------------------------------------------

class WorkoutScreen(QWidget):
    """Tela de treino ativo com QTableView + GhostValueDelegate."""

    session_finished = Signal()

    def __init__(
        self,
        db: DatabaseConnection,
        routine_manager: RoutineManager,
        analyzer: PerformanceAnalyzer,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._rm = routine_manager
        self._analyzer = analyzer
        self._session_id: int | None = None
        self._model: WorkoutEntryModel | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # Cabeçalho
        header_row = QHBoxLayout()
        self._title_label = QLabel("TREINO ATIVO")
        self._title_label.setObjectName("title")
        self._timer_label = QLabel("")
        self._timer_label.setObjectName("subtitle")
        header_row.addWidget(self._title_label)
        header_row.addStretch()
        header_row.addWidget(self._timer_label)
        layout.addLayout(header_row)

        # Tabela de séries
        self._table = QTableView()
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setEditTriggers(
            QTableView.DoubleClicked | QTableView.SelectedClicked
        )
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setDefaultSectionSize(38)
        self._table.setShowGrid(True)

        # Aplica delegate nas colunas de peso e reps
        delegate = GhostValueDelegate(self._table)
        self._table.setItemDelegateForColumn(COL_WEIGHT, delegate)
        self._table.setItemDelegateForColumn(COL_REPS, delegate)

        layout.addWidget(self._table)

        # Botões
        btn_row = QHBoxLayout()
        add_set_btn = QPushButton("+  ADICIONAR SÉRIE")
        add_set_btn.clicked.connect(self._add_row)

        self._finish_btn = QPushButton("■  FINALIZAR TREINO")
        self._finish_btn.setObjectName("danger")
        self._finish_btn.clicked.connect(self._finish_workout)

        btn_row.addWidget(add_set_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._finish_btn)
        layout.addLayout(btn_row)

    def load_routine(self, routine: Routine, session_id: int) -> None:
        """Carrega a rotina e pré-popula o modelo com os exercícios."""
        self._session_id = session_id
        exercises = self._rm.get_routine_exercises(routine.id)

        self._model = WorkoutEntryModel(
            db=self._db,
            session_id=session_id,
            analyzer=self._analyzer,
            exercises=exercises,
        )
        self._table.setModel(self._model)
        self._title_label.setText(f"⚡ {routine.name.upper()}")
        self._timer_label.setText("00:00")

    def _add_row(self) -> None:
        if self._model:
            self._model.insertRow(self._model.rowCount())

    def _finish_workout(self) -> None:
        if self._session_id is None:
            return

        confirm = QMessageBox.question(
            self,
            "Finalizar Treino",
            "Encerrar a sessão e salvar o log?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        duration = self._rm.end_session(self._session_id)
        total_volume = self._compute_total_volume()

        mins, secs = divmod(duration, 60)
        summary = (
            f"Treino finalizado!\n\n"
            f"Volume Total:  {total_volume:.1f} kg\n"
            f"Duração:       {mins:02d}:{secs:02d}"
        )
        QMessageBox.information(self, "Resumo da Sessão", summary)
        self.session_finished.emit()

    def _compute_total_volume(self) -> float:
        if self._session_id is None:
            return 0.0
        row = self._db.fetchone(
            "SELECT COALESCE(SUM(weight_kg * reps), 0.0) AS v FROM workout_logs WHERE session_id = ?",
            (self._session_id,),
        )
        return float(row["v"]) if row else 0.0



# ---------------------------------------------------------------------------
# Janela Principal
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """
    Janela principal com QStackedWidget gerenciando as telas.
    Instancia todos os componentes do motor e conecta os sinais.
    """

    SCREEN_DASHBOARD = 0
    SCREEN_WORKOUT   = 1

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GYMNight — Performance Engine")
        self.setMinimumSize(800, 560)
        self.resize(960, 640)

        # Motor
        self._db      = DatabaseConnection("gymnight.db")
        self._rm      = RoutineManager(self._db)
        self._norm    = NormalizationEngine(self._db)
        self._analyzer = PerformanceAnalyzer(self._db)

        # Worker thread para o analyzer
        self._worker_thread = QThread(self)
        self._analyzer.moveToThread(self._worker_thread)
        self._worker_thread.start()

        # Telas
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._dashboard = DashboardScreen(self._db, self._rm, self._norm)
        self._workout   = WorkoutScreen(self._db, self._rm, self._analyzer)

        self._stack.addWidget(self._dashboard)   # índice 0
        self._stack.addWidget(self._workout)     # índice 1

        # Conexões de navegação
        self._dashboard.routine_selected.connect(self._go_to_workout)
        self._workout.session_finished.connect(self._go_to_dashboard)

        self._stack.setCurrentIndex(self.SCREEN_DASHBOARD)

    def _go_to_workout(self, routine: Routine, session_id: int) -> None:
        self._workout.load_routine(routine, session_id)
        self._stack.setCurrentIndex(self.SCREEN_WORKOUT)

    def _go_to_dashboard(self) -> None:
        self._dashboard._load_routines()
        self._stack.setCurrentIndex(self.SCREEN_DASHBOARD)

    def closeEvent(self, event) -> None:
        self._worker_thread.quit()
        self._worker_thread.wait()
        self._db.close()
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
