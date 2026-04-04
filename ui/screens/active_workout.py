"""
ui/screens/active_workout.py
Tela de Treino Ativo: tabs por exercício, card de séries com check verde.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from database import DatabaseConnection
from engine import Exercise, NormalizationEngine, PerformanceAnalyzer, Routine, RoutineManager
from ui.theme import (
    C_BORDER, C_CARD, C_CARD2, C_GREEN, C_GREEN_BG,
    C_TEXT, C_TEXT2, C_TEXT3, label, separator,
)
from ui.delegates import SetTypeDelegate
from core.models import COL_SET_TYPE


class ActiveWorkoutScreen(QWidget):
    # Emite dict com: session_id, volume_total, duration_seconds, routine_name
    finished = Signal(dict)

    def __init__(self, db: DatabaseConnection, rm: RoutineManager,
                 analyzer: PerformanceAnalyzer, norm: NormalizationEngine, parent=None):
        super().__init__(parent)
        self._db       = db
        self._rm       = rm
        self._analyzer = analyzer
        self._norm     = norm
        self._session_id: int | None = None
        self._exercises: list[Exercise] = []
        self._current_idx = 0
        self._series_data: list[list[dict]] = []
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        back_btn = QPushButton("‹ Voltar")
        back_btn.setObjectName("ghost")
        back_btn.setFixedWidth(90)
        back_btn.clicked.connect(self._confirm_back)
        hdr.addWidget(back_btn)
        hdr.addStretch()
        self._series_counter = label("0/0 séries", "sub")
        hdr.addWidget(self._series_counter)
        lay.addLayout(hdr)

        self._title = label("TREINO", "h1")
        lay.addWidget(self._title)

        # Carregar Rotina
        load_row = QHBoxLayout()
        load_row.setSpacing(8)
        self._routine_combo = QComboBox()
        self._routine_combo.setMinimumWidth(260)
        self._routine_combo.setPlaceholderText("Selecionar rotina...")
        load_row.addWidget(self._routine_combo)
        load_btn = QPushButton("Carregar")
        load_btn.setFixedHeight(34)
        load_btn.clicked.connect(self._load_from_combo)
        load_row.addWidget(load_btn)
        load_row.addStretch()
        lay.addLayout(load_row)

        # Barra de progresso
        self._prog_bar = QFrame()
        self._prog_bar.setFixedHeight(4)
        self._prog_bar.setStyleSheet(f"background:{C_BORDER}; border-radius:2px;")
        self._prog_fill = QFrame(self._prog_bar)
        self._prog_fill.setFixedHeight(4)
        self._prog_fill.setStyleSheet(f"background:{C_GREEN}; border-radius:2px;")
        self._prog_fill.setFixedWidth(0)
        lay.addWidget(self._prog_bar)

        # Tabs de exercícios
        self._tabs_scroll = QScrollArea()
        self._tabs_scroll.setFixedHeight(48)
        self._tabs_scroll.setWidgetResizable(True)
        self._tabs_scroll.setFrameShape(QFrame.NoFrame)
        self._tabs_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._tabs_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._tabs_w = QWidget()
        self._tabs_lay = QHBoxLayout(self._tabs_w)
        self._tabs_lay.setContentsMargins(0, 0, 0, 0)
        self._tabs_lay.setSpacing(8)
        self._tabs_lay.addStretch()
        self._tabs_scroll.setWidget(self._tabs_w)
        lay.addWidget(self._tabs_scroll)

        # Card do exercício
        self._ex_card = QFrame()
        self._ex_card.setObjectName("card")
        ex_lay = QVBoxLayout(self._ex_card)
        ex_lay.setContentsMargins(20, 20, 20, 20)
        ex_lay.setSpacing(14)

        card_hdr = QHBoxLayout()
        self._ex_icon = QLabel("⚡")
        self._ex_icon.setFixedSize(44, 44)
        self._ex_icon.setAlignment(Qt.AlignCenter)
        self._ex_icon.setStyleSheet(f"background:{C_GREEN_BG}; color:{C_GREEN}; border-radius:10px; font-size:20px;")
        card_hdr.addWidget(self._ex_icon)
        card_hdr.addSpacing(12)

        card_info = QVBoxLayout()
        card_info.setSpacing(2)
        self._ex_name_lbl = label("", "h2")
        self._ex_meta_lbl = label("", "sub")
        card_info.addWidget(self._ex_name_lbl)
        card_info.addWidget(self._ex_meta_lbl)
        card_hdr.addLayout(card_info)
        card_hdr.addStretch()
        self._ex_prog_lbl = QLabel("0/4")
        self._ex_prog_lbl.setStyleSheet(f"color:{C_GREEN}; font-size:18px; font-weight:800;")
        card_hdr.addWidget(self._ex_prog_lbl)
        ex_lay.addLayout(card_hdr)

        # Cabeçalho séries
        s_hdr = QHBoxLayout()
        for txt, stretch in [("Série", 1), ("Peso (kg)", 3), ("Reps", 3), ("Tipo", 2), ("", 1)]:
            s_hdr.addWidget(label(txt, "sub"), stretch)
        ex_lay.addLayout(s_hdr)

        self._series_container = QVBoxLayout()
        self._series_container.setSpacing(8)
        ex_lay.addLayout(self._series_container)

        lay.addWidget(self._ex_card)
        lay.addStretch()

        # Navegação
        nav = QHBoxLayout()
        self._prev_btn = QPushButton("Anterior")
        self._prev_btn.setObjectName("ghost")
        self._prev_btn.setMinimumHeight(44)
        self._prev_btn.clicked.connect(self._prev)
        self._next_btn = QPushButton("Próximo")
        self._next_btn.setMinimumHeight(44)
        self._next_btn.clicked.connect(self._next)
        nav.addWidget(self._prev_btn, 1)
        nav.addWidget(self._next_btn, 2)
        lay.addLayout(nav)

    # ------------------------------------------------------------------
    # Carregamento
    # ------------------------------------------------------------------

    def _populate_routine_combo(self):
        """Preenche o QComboBox com as rotinas disponíveis."""
        self._routine_combo.clear()
        for r in self._rm.list_routines():
            self._routine_combo.addItem(r.name, userData=r)

    def _load_from_combo(self):
        """Carrega a rotina selecionada no combo sem iniciar sessão nova."""
        routine = self._routine_combo.currentData()
        if routine is None:
            return
        exercises = self._rm.get_routine_exercises(routine.id)
        self._exercises = exercises
        self._current_idx = 0
        self._series_data = [
            [{"weight": "", "reps": "", "set_type": "N", "done": False} for _ in range(4)]
            for _ in exercises
        ]
        self._title.setText(routine.name.upper())
        self._build_tabs()
        self._show_exercise(0)

    def load_routine(self, routine: Routine, session_id: int):
        self._session_id = session_id
        self._exercises  = self._rm.get_routine_exercises(routine.id)
        self._current_idx = 0
        self._title.setText(routine.name.upper())
        self._series_data = [
            [{"weight": "", "reps": "", "set_type": "N", "done": False} for _ in range(4)]
            for _ in self._exercises
        ]
        self._populate_routine_combo()
        # Seleciona a rotina atual no combo
        for i in range(self._routine_combo.count()):
            if self._routine_combo.itemData(i).id == routine.id:
                self._routine_combo.setCurrentIndex(i)
                break
        self._build_tabs()
        self._show_exercise(0)

    def _build_tabs(self):
        while self._tabs_lay.count() > 1:
            item = self._tabs_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, ex in enumerate(self._exercises):
            short = ex.canonical_name.title()
            if len(short) > 16:
                short = short[:14] + "…"
            btn = QPushButton(f"{i+1}. {short}")
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:{C_CARD}; color:{C_TEXT3};
                    border:1px solid {C_BORDER}; border-radius:17px;
                    padding:0 14px; font-size:12px; font-weight:600;
                }}
                QPushButton:checked {{
                    background:{C_GREEN}; color:#000; border-color:{C_GREEN};
                }}
            """)
            btn.clicked.connect(lambda _, idx=i: self._show_exercise(idx))
            self._tabs_lay.insertWidget(i, btn)

    def _show_exercise(self, idx: int):
        if not self._exercises:
            return
        self._current_idx = idx
        ex = self._exercises[idx]

        for i in range(len(self._exercises)):
            item = self._tabs_lay.itemAt(i)
            if item and item.widget():
                item.widget().setChecked(i == idx)

        self._ex_name_lbl.setText(ex.canonical_name.upper())
        self._ex_meta_lbl.setText("4 séries × 8-12 reps — Descanso: 60s")

        series = self._series_data[idx]
        done = sum(1 for s in series if s["done"])
        self._ex_prog_lbl.setText(f"{done}/{len(series)}")

        while self._series_container.count():
            item = self._series_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for s_idx, s in enumerate(series):
            row_w = QWidget()
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(8)

            num = label(str(s_idx + 1), "sub")
            num.setFixedWidth(30)
            row_lay.addWidget(num, 1)

            w_edit = QLineEdit(s["weight"])
            w_edit.setPlaceholderText("0")
            w_edit.setAlignment(Qt.AlignCenter)
            w_edit.textChanged.connect(lambda v, i=idx, j=s_idx: self._update(i, j, "weight", v))
            row_lay.addWidget(w_edit, 3)

            r_edit = QLineEdit(s["reps"])
            r_edit.setPlaceholderText("0")
            r_edit.setAlignment(Qt.AlignCenter)
            r_edit.textChanged.connect(lambda v, i=idx, j=s_idx: self._update(i, j, "reps", v))
            row_lay.addWidget(r_edit, 3)

            # Dropdown de tipo de série
            type_combo = QComboBox()
            type_combo.setFixedHeight(34)
            type_combo.setStyleSheet(f"background:{C_CARD}; color:#e0e0e0; border:1px solid {C_BORDER}; border-radius:6px; padding:2px 6px; font-size:11px; font-weight:600;")
            _SET_TYPE_COLORS = {"N": "#9ca3af", "W": "#60a5fa", "D": "#f97316", "F": "#ef4444"}
            from core.models import SET_TYPES
            for code, name in SET_TYPES:
                type_combo.addItem(f"[{code}] {name}", userData=code)
            current_type = s.get("set_type", "N")
            for ti in range(type_combo.count()):
                if type_combo.itemData(ti) == current_type:
                    type_combo.setCurrentIndex(ti)
                    break
            type_combo.currentIndexChanged.connect(
                lambda _, i=idx, j=s_idx, cb=type_combo: self._update(i, j, "set_type", cb.currentData())
            )
            row_lay.addWidget(type_combo, 2)

            check = QPushButton("✓")
            check.setFixedSize(40, 40)
            check.setCheckable(True)
            check.setChecked(s["done"])
            self._style_check(check, s["done"])
            check.clicked.connect(lambda checked, i=idx, j=s_idx, b=check: self._toggle_done(i, j, checked, b))
            row_lay.addWidget(check, 1)

            self._series_container.addWidget(row_w)

        self._update_progress()
        self._prev_btn.setEnabled(idx > 0)
        self._next_btn.setText("Finalizar" if idx == len(self._exercises) - 1 else "Próximo")

    def _style_check(self, btn: QPushButton, done: bool):
        if done:
            btn.setStyleSheet(f"background:{C_GREEN}; color:#000; border-radius:10px; font-size:16px; font-weight:700; border:none;")
        else:
            btn.setStyleSheet(f"background:{C_CARD2}; color:{C_TEXT3}; border-radius:10px; font-size:16px; border:1px solid {C_BORDER};")

    def _update(self, ex_idx: int, s_idx: int, key: str, val: str):
        self._series_data[ex_idx][s_idx][key] = val

    def _toggle_done(self, ex_idx: int, s_idx: int, checked: bool, btn: QPushButton):
        self._series_data[ex_idx][s_idx]["done"] = checked
        self._style_check(btn, checked)
        series = self._series_data[ex_idx]
        done = sum(1 for s in series if s["done"])
        self._ex_prog_lbl.setText(f"{done}/{len(series)}")
        self._update_progress()
        if checked and self._session_id:
            s = self._series_data[ex_idx][s_idx]
            try:
                w = float(s["weight"]) if s["weight"] else 0.0
                r = int(s["reps"]) if s["reps"] else 0
                if w > 0 and r > 0:
                    self._db.execute_write(
                        "INSERT INTO workout_logs (exercise_id, session_id, weight_kg, reps, set_type) VALUES (?,?,?,?,?)",
                        (self._exercises[ex_idx].id, self._session_id, w, r, s.get("set_type", "N")),
                    )
            except (ValueError, TypeError):
                pass

    def _update_progress(self):
        total = sum(len(s) for s in self._series_data)
        done  = sum(sum(1 for x in s if x["done"]) for s in self._series_data)
        self._series_counter.setText(f"{done}/{total} séries")
        if total > 0:
            QTimer.singleShot(0, lambda: self._prog_fill.setFixedWidth(
                int(self._prog_bar.width() * done / total)
            ))

    def _prev(self):
        if self._current_idx > 0:
            self._show_exercise(self._current_idx - 1)

    def _next(self):
        if self._current_idx < len(self._exercises) - 1:
            self._show_exercise(self._current_idx + 1)
        else:
            self._finish()

    def _finish(self):
        if QMessageBox.question(self, "Finalizar", "Encerrar sessão?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        duration = self._rm.end_session(self._session_id) if self._session_id else 0
        row = self._db.fetchone(
            "SELECT COALESCE(SUM(weight_kg*reps),0) AS v FROM workout_logs WHERE session_id=?",
            (self._session_id,),
        )
        vol = float(row["v"]) if row else 0.0
        mins, secs = divmod(duration, 60)
        QMessageBox.information(self, "Treino Finalizado",
            f"Volume Total: {vol:.0f} kg\nDuração: {mins:02d}:{secs:02d}")

        payload = {
            "session_id":       self._session_id,
            "volume_total":     vol,
            "duration_seconds": duration,
            "routine_name":     self._title.text(),
        }
        self._session_id = None
        self.finished.emit(payload)

    def _confirm_back(self):
        if QMessageBox.question(self, "Voltar", "Abandonar o treino atual?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self._session_id = None
            self.finished.emit({})
