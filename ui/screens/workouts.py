"""
ui/screens/workouts.py
Tela de Treinos: barra de pesquisa, lista de rotinas, botão + Cardio avulso.
"""
from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QScrollArea,
    QSlider, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)

from database import DatabaseConnection
from engine import NormalizationEngine, Routine, RoutineManager
from ui.dialogs import ExerciseLineEdit
from ui.theme import (
    C_BORDER, C_CARD, C_CARD2, C_GREEN, C_GREEN_BG,
    C_TEXT, C_TEXT2, C_TEXT3, label, separator,
    RADIUS_MD, RADIUS_SM,
)
from ui.widgets import RoutineCard


class WorkoutsTab(QWidget):
    start_workout  = Signal(object, int)   # (Routine, session_id)
    add_cardio_req = Signal()              # abre diálogo de cardio avulso

    def __init__(self, db: DatabaseConnection, rm: RoutineManager,
                 norm: NormalizationEngine, parent=None):
        super().__init__(parent)
        self._db       = db
        self._rm       = rm
        self._norm     = norm
        self._all_cards: list[tuple[Routine, RoutineCard]] = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        # ── Página 0: lista de treinos ────────────────────────────────────
        list_page = QWidget()
        lay = QVBoxLayout(list_page)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        hdr = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(2)
        h = QLabel("SEUS <span style='color:#a3e635'>TREINOS</span>")
        h.setTextFormat(Qt.RichText)
        h.setStyleSheet("font-size:26px; font-weight:800; color:#fff;")
        left.addWidget(h)
        left.addWidget(label("Divisão ABC + seus treinos personalizados", "sub"))
        hdr.addLayout(left)
        hdr.addStretch()

        cardio_btn = QPushButton(" Cardio")
        cardio_btn.setIcon(qta.icon("fa5s.heart", color=C_GREEN))
        cardio_btn.setFixedHeight(38)
        cardio_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C_GREEN};
                border: 1px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                padding: 0 16px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {C_GREEN_BG}; }}
            QPushButton:pressed {{ background: {C_GREEN}; color: #000; }}
        """)
        cardio_btn.clicked.connect(self._open_cardio)
        hdr.addWidget(cardio_btn)

        new_btn = QPushButton(" Novo Treino")
        new_btn.setIcon(qta.icon("fa5s.plus", color="#000000"))
        new_btn.setFixedHeight(38)
        new_btn.clicked.connect(self._show_create_form)
        hdr.addWidget(new_btn)
        lay.addLayout(hdr)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Pesquisar treino...")
        self._search.setFixedHeight(40)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {C_CARD};
                color: {C_TEXT};
                border: 1px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 0 14px 0 36px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {C_GREEN};
            }}
        """)
        self._search.textChanged.connect(self._filter_routines)
        lay.addWidget(self._search)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._list_w = QWidget()
        self._list_lay = QVBoxLayout(self._list_w)
        self._list_lay.setContentsMargins(0, 0, 0, 0)
        self._list_lay.setSpacing(10)
        self._list_lay.addStretch()
        scroll.setWidget(self._list_w)
        lay.addWidget(scroll)

        self._stack.addWidget(list_page)  # index 0

        # ── Página 1: formulário de criação ───────────────────────────────
        self._stack.addWidget(self._build_create_page())  # index 1
        self._stack.addWidget(self._build_cardio_page())   # index 2

        self.reload()

    # ------------------------------------------------------------------
    # Pesquisa
    # ------------------------------------------------------------------

    def _filter_routines(self, query: str):
        """Filtra os cards de rotina pelo nome em tempo real."""
        q = query.strip().lower()
        for routine, card in self._all_cards:
            visible = q == "" or q in routine.name.lower()
            card.setVisible(visible)

    # ------------------------------------------------------------------
    # Cardio avulso
    # ------------------------------------------------------------------

    def _open_cardio(self):
        self._cardio_search.clear()
        self._cardio_duration.setValue(30)
        self._cardio_distance.setValue(0)
        self._cardio_pse.setValue(5)
        self._stack.setCurrentIndex(2)

    def _build_cardio_page(self) -> QWidget:
        from ui.screens.cardio_widget import parse_cardio_types
        self._cardio_types = parse_cardio_types()

        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        # Cabeçalho
        hdr = QHBoxLayout()
        back_btn = QPushButton("← Voltar")
        back_btn.setObjectName("ghost")
        back_btn.setFixedWidth(90)
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        hdr.addWidget(back_btn)
        hdr.addStretch()
        outer.addLayout(hdr)

        outer.addWidget(label("CARDIO AVULSO", "h2"))
        outer.addWidget(label("Registre uma atividade cardiovascular fora do treino.", "sub"))
        outer.addWidget(separator())

        # Tipo de cardio
        outer.addWidget(label("Tipo de Cardio", "h3"))
        self._cardio_search = QLineEdit()
        self._cardio_search.setPlaceholderText("Ex: Esteira, Corrida, Bicicleta...")
        self._cardio_search.setFixedHeight(42)
        self._cardio_search.setStyleSheet(f"""
            QLineEdit {{
                background: {C_CARD};
                color: {C_TEXT};
                border: 1px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                padding: 0 14px;
                font-size: 13px;
            }}
        """)
        outer.addWidget(self._cardio_search)

        # Popup flutuante de resultados
        self._cardio_popup = QListWidget(page)
        self._cardio_popup.setWindowFlags(Qt.ToolTip)
        self._cardio_popup.setFocusPolicy(Qt.NoFocus)
        self._cardio_popup.setStyleSheet(f"""
            QListWidget {{
                background: {C_CARD};
                border: 1px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                outline: none;
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 9px 14px;
                color: {C_TEXT2};
                border-bottom: 1px solid {C_BORDER};
            }}
            QListWidget::item:hover {{ background: {C_CARD2}; color: {C_TEXT}; }}
            QListWidget::item:selected {{ background: #1a2e1a; color: {C_GREEN}; }}
        """)
        self._cardio_popup.hide()
        self._cardio_popup.itemClicked.connect(self._cardio_on_item_clicked)

        self._cardio_filter_timer = QTimer(self)
        self._cardio_filter_timer.setSingleShot(True)
        self._cardio_filter_timer.setInterval(100)
        self._cardio_filter_timer.timeout.connect(self._cardio_update_popup)
        self._cardio_search.textChanged.connect(lambda _: self._cardio_filter_timer.start())
        self._cardio_search.mousePressEvent = lambda e: (
            QLineEdit.mousePressEvent(self._cardio_search, e),
            self._cardio_update_popup()
        )
        self._cardio_search.installEventFilter(self)

        # Métricas
        metrics = QFrame()
        metrics.setObjectName("card")
        m_lay = QVBoxLayout(metrics)
        m_lay.setContentsMargins(16, 16, 16, 16)
        m_lay.setSpacing(12)

        row1 = QHBoxLayout()
        row1.addWidget(label("Tempo (min) *", "h3"), 1)
        self._cardio_duration = QDoubleSpinBox()
        self._cardio_duration.setRange(1, 300)
        self._cardio_duration.setValue(30)
        self._cardio_duration.setSuffix(" min")
        self._cardio_duration.setDecimals(0)
        self._cardio_duration.setMinimumWidth(120)
        row1.addWidget(self._cardio_duration, 1)
        m_lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(label("Distância (km)", "h3"), 1)
        self._cardio_distance = QDoubleSpinBox()
        self._cardio_distance.setRange(0, 200)
        self._cardio_distance.setValue(0)
        self._cardio_distance.setSuffix(" km")
        self._cardio_distance.setDecimals(1)
        self._cardio_distance.setSpecialValueText("—")
        self._cardio_distance.setMinimumWidth(120)
        row2.addWidget(self._cardio_distance, 1)
        m_lay.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(label("Esforço (PSE 1-10)", "h3"), 1)
        pse_col = QVBoxLayout()
        self._cardio_pse = QSlider(Qt.Horizontal)
        self._cardio_pse.setRange(1, 10)
        self._cardio_pse.setValue(5)
        self._cardio_pse.setTickPosition(QSlider.TicksBelow)
        self._cardio_pse.setTickInterval(1)
        self._cardio_pse.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 6px; background: {C_CARD2}; border-radius: {RADIUS_SM}px;
            }}
            QSlider::handle:horizontal {{
                background: {C_GREEN}; width: 18px; height: 18px;
                margin: -6px 0; border-radius: 9px;
            }}
            QSlider::sub-page:horizontal {{
                background: {C_GREEN}; border-radius: {RADIUS_SM}px;
            }}
        """)
        self._cardio_pse_lbl = QLabel("5")
        self._cardio_pse_lbl.setStyleSheet(
            f"color:{C_GREEN}; font-size:18px; font-weight:800; min-width:24px; font-family:'Arial';"
        )
        self._cardio_pse_lbl.setAlignment(Qt.AlignCenter)
        self._cardio_pse.valueChanged.connect(lambda v: self._cardio_pse_lbl.setText(str(v)))
        pse_row = QHBoxLayout()
        pse_row.addWidget(self._cardio_pse)
        pse_row.addWidget(self._cardio_pse_lbl)
        pse_col.addLayout(pse_row)
        ref_row = QHBoxLayout()
        for txt in ["Leve", "Moderado", "Intenso", "Máximo"]:
            lbl = QLabel(txt)
            lbl.setStyleSheet(f"color:{C_TEXT3}; font-size:10px;")
            lbl.setAlignment(Qt.AlignCenter)
            ref_row.addWidget(lbl)
        pse_col.addLayout(ref_row)
        row3.addLayout(pse_col, 2)
        m_lay.addLayout(row3)

        outer.addWidget(metrics)
        outer.addStretch()

        save_btn = QPushButton("＋ Registrar Cardio")
        save_btn.setMinimumHeight(44)
        save_btn.clicked.connect(self._save_cardio)
        outer.addWidget(save_btn)

        return page

    def _cardio_update_popup(self):
        import unicodedata
        def norm(t):
            nfd = unicodedata.normalize("NFD", t.lower().strip())
            return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

        query = norm(self._cardio_search.text())
        self._cardio_popup.clear()
        matches = [ct for ct in self._cardio_types if query == "" or query in norm(ct["name"])]
        if not matches:
            self._cardio_popup.hide()
            return
        for ct in matches[:20]:
            intensity = ct.get("intensity", "")
            text = f"{ct['name']}  [{intensity}]" if intensity else ct["name"]
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, ct["name"])
            self._cardio_popup.addItem(item)
        pos = self._cardio_search.mapToGlobal(self._cardio_search.rect().bottomLeft())
        self._cardio_popup.setFixedWidth(self._cardio_search.width())
        row_h = self._cardio_popup.sizeHintForRow(0) if self._cardio_popup.count() > 0 else 36
        self._cardio_popup.setFixedHeight(min(280, row_h * min(self._cardio_popup.count(), 8) + 8))
        self._cardio_popup.move(pos)
        self._cardio_popup.show()
        self._cardio_popup.raise_()

    def _cardio_on_item_clicked(self, item: QListWidgetItem):
        self._cardio_search.blockSignals(True)
        self._cardio_search.setText(item.data(Qt.UserRole))
        self._cardio_search.blockSignals(False)
        self._cardio_popup.hide()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self._cardio_search:
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Down and self._cardio_popup.isVisible():
                    self._cardio_popup.setFocus()
                    self._cardio_popup.setCurrentRow(0)
                    return True
                if event.key() == Qt.Key_Escape:
                    self._cardio_popup.hide()
                    return True
            if event.type() == QEvent.FocusOut:
                QTimer.singleShot(150, self._cardio_popup.hide)
        return super().eventFilter(obj, event)

    def _save_cardio(self):
        name = self._cardio_search.text().strip()
        if not name:
            QMessageBox.warning(self, "Atenção", "Selecione o tipo de cardio.")
            return
        dist = self._cardio_distance.value()
        session_id = self._db.execute_write(
            "INSERT INTO workout_sessions DEFAULT VALUES"
        )
        self._db.execute_write(
            "INSERT INTO cardio_logs (session_id, cardio_type, duration_min, distance_km, pse) VALUES (?,?,?,?,?)",
            (session_id, name, self._cardio_duration.value(),
             dist if dist > 0 else None, self._cardio_pse.value()),
        )
        self._db.execute_write(
            "UPDATE workout_sessions SET duration_seconds=? WHERE id=?",
            (int(self._cardio_duration.value() * 60), session_id),
        )
        QMessageBox.information(
            self, "Cardio Registrado",
            f"✓ {name}\n◷ {int(self._cardio_duration.value())} min"
            + (f" · {dist:.1f} km" if dist > 0 else "")
            + f"\n◈ PSE {self._cardio_pse.value()}/10",
        )
        self._stack.setCurrentIndex(0)



    # ------------------------------------------------------------------
    # Formulário inline de criação
    # ------------------------------------------------------------------

    def _build_create_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(8)

        # Cabeçalho com botão voltar
        hdr = QHBoxLayout()
        back_btn = QPushButton("← Voltar")
        back_btn.setObjectName("ghost")
        back_btn.setFixedWidth(90)
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        hdr.addWidget(back_btn)
        hdr.addStretch()
        outer.addLayout(hdr)

        outer.addWidget(label("CRIAR TREINO", "h2"))
        outer.addWidget(label("Monte seu treino personalizado com exercícios, séries e repetições.", "sub"))
        outer.addWidget(separator())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        form_w = QWidget()
        self._form_lay = QVBoxLayout(form_w)
        self._form_lay.setSpacing(4)
        scroll.setWidget(form_w)
        outer.addWidget(scroll)

        # Nome
        self._form_lay.addWidget(label("Nome do treino", "h3"))
        self._name = QLineEdit()
        self._name.setPlaceholderText("Ex: Treino D — Ombro")
        self._form_lay.addWidget(self._name)

        # Dia + Músculos
        row = QHBoxLayout()
        row.setSpacing(12)
        for attr, lbl_txt, ph in [
            ("_days",    "Dia(s)",    "Ex: Segunda"),
            ("_muscles", "Músculos",  "Ex: Ombro & Trapézio"),
        ]:
            col = QVBoxLayout()
            col.setSpacing(4)
            col.addWidget(label(lbl_txt, "h3"))
            edit = QLineEdit()
            edit.setPlaceholderText(ph)
            setattr(self, attr, edit)
            col.addWidget(edit)
            row.addLayout(col)
        self._form_lay.addLayout(row)

        # Exercícios
        self._ex_widgets: list[dict] = []
        self._form_lay.addWidget(label("Exercícios", "h3"))
        self._ex_container = QVBoxLayout()
        self._ex_container.setSpacing(10)
        self._form_lay.addLayout(self._ex_container)
        self._add_exercise_block()

        add_ex = QPushButton(" Adicionar exercício")
        add_ex.setIcon(qta.icon("fa5s.plus", color=C_TEXT2, options=[{"scale_factor": 0.6}]))
        add_ex.setObjectName("ghost")
        add_ex.clicked.connect(self._add_exercise_block)
        self._form_lay.addWidget(add_ex)

        save = QPushButton(" Salvar Treino")
        save.setIcon(qta.icon("fa5s.save", color="#000000"))
        save.setMinimumHeight(44)
        save.clicked.connect(self._save_workout)
        outer.addWidget(save)

        return page

    def _add_exercise_block(self):
        idx = len(self._ex_widgets) + 1
        block = QFrame()
        block.setObjectName("card")
        b_lay = QVBoxLayout(block)
        b_lay.setContentsMargins(12, 12, 12, 12)
        b_lay.setSpacing(8)
        b_lay.addWidget(label(f"Exercício {idx}", "sub"))

        name_edit = ExerciseLineEdit(self._norm, block)
        b_lay.addWidget(name_edit)

        row = QHBoxLayout()
        series = QSpinBox()
        series.setRange(1, 20)
        series.setValue(3)
        reps = QLineEdit("10-12")
        rest = QLineEdit("60s")
        for w, lbl_txt in [(series, "Séries"), (reps, "Reps"), (rest, "Descanso")]:
            col = QVBoxLayout()
            col.addWidget(label(lbl_txt, "sub"))
            col.addWidget(w)
            row.addLayout(col)
        b_lay.addLayout(row)

        self._ex_container.addWidget(block)
        self._ex_widgets.append({"name": name_edit, "series": series, "reps": reps, "rest": rest})

    def _show_create_form(self):
        # Limpa o formulário antes de exibir
        self._name.clear()
        self._days.clear()
        self._muscles.clear()
        # Remove blocos de exercício existentes
        while self._ex_container.count():
            item = self._ex_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._ex_widgets.clear()
        self._add_exercise_block()
        self._stack.setCurrentIndex(1)

    def _save_workout(self):
        exercises = []
        for w in self._ex_widgets:
            n = w["name"].text().strip()
            if n:
                exercises.append({
                    "name": n,
                    "series": w["series"].value(),
                    "reps": w["reps"].text(),
                    "rest": w["rest"].text(),
                })
        name = self._name.text().strip()
        if not name or not exercises:
            QMessageBox.warning(self, "Atenção", "Informe nome e ao menos um exercício.")
            return
        ex_ids = [self._norm.get_or_create(e["name"]).id for e in exercises]
        self._rm.create_routine(name, ex_ids)
        self._stack.setCurrentIndex(0)
        self.reload()



    def reload(self):
        self._all_cards.clear()
        while self._list_lay.count() > 1:
            item = self._list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        routines = self._rm.list_routines()
        if not routines:
            empty = label(
                "Nenhum treino criado ainda.\nClique em '+ Novo Treino' para começar.",
                "sub",
            )
            empty.setAlignment(Qt.AlignCenter)
            self._list_lay.insertWidget(0, empty)
            return

        for i, r in enumerate(routines):
            exs = self._rm.get_routine_exercises(r.id)
            c = RoutineCard(r, exs)
            c.start_clicked.connect(self._on_start)
            c.edit_clicked.connect(self._on_edit)
            self._list_lay.insertWidget(i, c)
            self._all_cards.append((r, c))

        # Reaplica filtro se houver texto na busca
        if self._search.text():
            self._filter_routines(self._search.text())

    def _on_start(self, routine: Routine):
        session_id = self._db.execute_write(
            "INSERT INTO workout_sessions (routine_id) VALUES (?)", (routine.id,)
        )
        self.start_workout.emit(routine, session_id)

    def _on_edit(self, routine: Routine):
        """Abre diálogo para editar nome e exercícios da rotina."""
        from ui.screens.edit_routine_dialog import EditRoutineDialog
        dlg = EditRoutineDialog(routine, self._rm, self._norm, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.reload()
