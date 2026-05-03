"""
ui/screens/active_workout.py
Tela de Treino Ativo: força + cardio, tabs por exercício, card de séries.
"""
from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from database import DatabaseConnection
from engine import Exercise, NormalizationEngine, PerformanceAnalyzer, Routine, RoutineManager
from src.ui.theme import (
    C_BORDER, C_CARD, C_CARD2, C_GREEN, C_GREEN_BG,
    C_TEXT, C_TEXT2, C_TEXT3, label, separator, neon_glow,
    RADIUS_SM, RADIUS_MD, RADIUS_LG,
)
from src.ui.screens.cardio_widget import CardioPickerDialog, CardioRow
from src.ui.widgets.set_indicator import SetIndicatorWidget
from src.ui.widgets.muscle_heatmap import MuscleHeatmapWidget
from src.ui_models.models import SET_TYPES


class ActiveWorkoutScreen(QWidget):
    # Emite dict: session_id, volume_total, duration_seconds, routine_name,
    #             cardio_total_min, cardio_avg_pse, cardio_count
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
        self._cardio_rows: list[CardioRow] = []
        self._finish_payload: dict = {}
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._main_stack = QStackedWidget()
        root.addWidget(self._main_stack)

        # ── Página 0: tela de treino ──────────────────────────────────────
        workout_page = QWidget()
        workout_root = QVBoxLayout(workout_page)
        workout_root.setContentsMargins(0, 0, 0, 0)
        workout_root.setSpacing(0)

        # Scroll principal
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        back_btn = QPushButton(" Voltar")
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color=C_TEXT2))
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

        # Botão para adicionar exercício avulso
        add_ex_row = QHBoxLayout()
        add_ex_row.setSpacing(8)
        
        add_ex_btn = QPushButton(" Adicionar Exercício")
        add_ex_btn.setIcon(qta.icon("fa5s.plus", color=C_GREEN))
        add_ex_btn.setFixedHeight(40)
        add_ex_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C_GREEN};
                border: 1px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                padding: 0 16px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: rgba(162, 255, 0, 0.12); }}
        """)
        add_ex_btn.clicked.connect(self._add_exercise_dialog)
        add_ex_row.addWidget(add_ex_btn)
        add_ex_row.addStretch()
        lay.addLayout(add_ex_row)

        # Barra de progresso
        self._prog_bar = QFrame()
        self._prog_bar.setFixedHeight(4)
        self._prog_bar.setStyleSheet(f"background:{C_BORDER}; border-radius:{RADIUS_SM}px;")
        self._prog_fill = QFrame(self._prog_bar)
        self._prog_fill.setFixedHeight(4)
        self._prog_fill.setStyleSheet(f"background:{C_GREEN}; border-radius:{RADIUS_SM}px;")
        self._prog_fill.setFixedWidth(0)
        lay.addWidget(self._prog_bar)

        # Container para todos os cards de exercícios
        self._exercises_container = QVBoxLayout()
        self._exercises_container.setSpacing(32)
        lay.addLayout(self._exercises_container)

        # ── Seção de Cardio ──────────────────────────────────────────────
        cardio_hdr = QHBoxLayout()
        cardio_title = label("CARDIO", "h3")
        cardio_hdr.addWidget(cardio_title)
        cardio_hdr.addStretch()
        add_cardio_btn = QPushButton(" Cardio")
        add_cardio_btn.setIcon(qta.icon("fa5s.heartbeat", color=C_GREEN))
        add_cardio_btn.setFixedHeight(34)
        add_cardio_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C_GREEN};
                border: 1px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                padding: 0 14px;
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: rgba(162, 255, 0, 0.12); }}
        """)
        add_cardio_btn.clicked.connect(self._add_cardio)
        cardio_hdr.addWidget(add_cardio_btn)
        lay.addLayout(cardio_hdr)

        self._cardio_container = QVBoxLayout()
        self._cardio_container.setSpacing(8)
        lay.addLayout(self._cardio_container)

        self._no_cardio_lbl = label("Nenhum cardio adicionado.", "sub")
        self._no_cardio_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._no_cardio_lbl)

        lay.addStretch()
        scroll.setWidget(content)
        workout_root.addWidget(scroll)

        # Botão de finalizar (fora do scroll, fixo no rodapé)
        nav_w = QWidget()
        nav_w.setStyleSheet(f"background:{C_CARD}; border-top:1px solid {C_BORDER};")
        nav = QHBoxLayout(nav_w)
        nav.setContentsMargins(24, 10, 24, 10)
        nav.setSpacing(12)

        self._finish_btn = QPushButton(" Finalizar Treino")
        self._finish_btn.setIcon(qta.icon("fa5s.flag-checkered", color="#000000"))
        self._finish_btn.setMinimumHeight(48)
        self._finish_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_GREEN};
                color: #000;
                border: none;
                border-radius: {RADIUS_MD}px;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background: #bef264; }}
        """)
        self._finish_btn.clicked.connect(self._finish)

        nav.addWidget(self._finish_btn)
        workout_root.addWidget(nav_w)

        self._main_stack.addWidget(workout_page)  # index 0

        # ── Página 1: tela de resumo (finalizar treino) ───────────────────
        self._main_stack.addWidget(self._build_summary_page())  # index 1

    # ------------------------------------------------------------------
    # Adicionar exercício avulso
    # ------------------------------------------------------------------

    def _add_exercise_dialog(self):
        """Abre diálogo para adicionar exercício avulso ao treino."""
        from src.ui.dialogs import ExerciseLineEdit, FramelessDialog
        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        
        dlg = FramelessDialog("ADICIONAR EXERCÍCIO", self)
        dlg.setMinimumWidth(500)
        dlg.setMaximumHeight(400)
        
        lay = dlg.content_layout()
        lay.addWidget(label("Buscar exercício", "h3"))
        
        # Campo de busca com popup
        search = QLineEdit()
        search.setPlaceholderText("Digite para buscar exercício...")
        search.setFixedHeight(44)
        lay.addWidget(search)
        
        # Popup de resultados
        popup = QListWidget(dlg)
        popup.setMaximumHeight(250)
        popup.setStyleSheet(f"""
            QListWidget {{
                background: #1e1e1e;
                border: 1px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                font-size: 14px;
            }}
            QListWidget::item {{ padding: 10px 14px; color: {C_TEXT2}; }}
            QListWidget::item:hover {{ background: #2a2a2a; color: {C_TEXT}; }}
            QListWidget::item:selected {{ background: #1a2e1a; color: {C_GREEN}; }}
        """)
        lay.addWidget(popup)
        
        selected_exercise = [None]  # Lista para capturar o exercício selecionado
        
        def on_search_changed(text):
            if not text.strip():
                popup.clear()
                return
            
            # Normaliza o texto de busca
            search_normalized = self._norm._normalize_text(text)
            
            # Busca todos os exercícios
            rows = self._norm._db.fetchall(
                "SELECT id, canonical_name, user_input_name FROM exercises ORDER BY canonical_name"
            )
            
            # Busca exercícios com MET
            met_rows = self._norm._db.fetchall("SELECT exercise_id FROM exercise_met_values")
            met_exercises = {row["exercise_id"] for row in met_rows}
            
            # Filtra por substring
            matches = []
            for row in rows:
                canonical = row["canonical_name"]
                if search_normalized in canonical:
                    # Prioriza exercícios com MET
                    if row["id"] in met_exercises:
                        ex = self._norm._load_exercise(row["id"], canonical, row["user_input_name"])
                        matches.append(ex)
                    
                    if len(matches) >= 20:
                        break
            
            # Adiciona exercícios sem MET se houver espaço
            if len(matches) < 20:
                for row in rows:
                    canonical = row["canonical_name"]
                    if search_normalized in canonical and row["id"] not in met_exercises:
                        ex = self._norm._load_exercise(row["id"], canonical, row["user_input_name"])
                        matches.append(ex)
                        
                        if len(matches) >= 20:
                            break
            
            popup.clear()
            for ex in matches:
                met_indicator = " 🔥" if ex.id in met_exercises else ""
                item = QListWidgetItem(f"{ex.canonical_name.title()}  [{ex.muscle_group_name}]{met_indicator}")
                item.setData(Qt.UserRole, ex)
                popup.addItem(item)
        
        def on_item_clicked(item):
            selected_exercise[0] = item.data(Qt.UserRole)
            dlg.accept()
        
        search.textChanged.connect(on_search_changed)
        popup.itemClicked.connect(on_item_clicked)
        
        # Botões
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("ghost")
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_cancel)
        
        btn_add = QPushButton(" Adicionar")
        btn_add.setIcon(qta.icon("fa5s.plus", color="#000000"))
        btn_add.clicked.connect(lambda: dlg.accept() if popup.currentItem() else None)
        btn_row.addWidget(btn_add)
        lay.addLayout(btn_row)
        
        if dlg.exec() == QDialog.Accepted and selected_exercise[0]:
            self._add_exercise_to_workout(selected_exercise[0])

    def _add_exercise_to_workout(self, exercise: Exercise):
        """Adiciona um exercício avulso ao treino atual."""
        if not self._session_id:
            QMessageBox.warning(self, "Atenção", "Inicie um treino antes de adicionar exercícios.")
            return
        
        # Adiciona o exercício à lista
        self._exercises.append(exercise)
        
        # Adiciona séries padrão para o novo exercício
        self._series_data.append([
            {"weight": "", "reps": "", "set_type": "N", "done": False, "saved": False}
            for _ in range(4)
        ])
        
        # Reconstrói todos os cards
        self._build_all_exercises()
        
        QMessageBox.information(self, "Sucesso", f"Exercício '{exercise.canonical_name.title()}' adicionado!")

    # ------------------------------------------------------------------
    # Cardio
    # ------------------------------------------------------------------

    def _add_cardio(self):
        dlg = CardioPickerDialog(parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.get_data()
        if not data:
            return
        row = CardioRow(data, parent=None)
        row.remove_requested.connect(self._remove_cardio)
        self._cardio_rows.append(row)
        self._cardio_container.addWidget(row)
        self._no_cardio_lbl.setVisible(len(self._cardio_rows) == 0)

    def _remove_cardio(self, row: CardioRow):
        if row in self._cardio_rows:
            self._cardio_rows.remove(row)
        self._cardio_container.removeWidget(row)
        row.deleteLater()
        self._no_cardio_lbl.setVisible(len(self._cardio_rows) == 0)

    def _save_cardio_logs(self):
        """Persiste todos os registros de cardio no banco."""
        if not self._session_id or not self._cardio_rows:
            return
        for row in self._cardio_rows:
            d = row.get_data()
            self._db.execute_write(
                "INSERT INTO cardio_logs (session_id, cardio_type, duration_min, distance_km, pse) VALUES (?,?,?,?,?)",
                (self._session_id, d["cardio_type"], d["duration_min"],
                 d.get("distance_km"), d.get("pse")),
            )

    def _cardio_summary(self) -> dict:
        total_min = sum(r.get_data()["duration_min"] for r in self._cardio_rows)
        pse_vals  = [r.get_data()["pse"] for r in self._cardio_rows if r.get_data().get("pse")]
        avg_pse   = round(sum(pse_vals) / len(pse_vals), 1) if pse_vals else 0
        return {
            "cardio_total_min": total_min,
            "cardio_avg_pse":   avg_pse,
            "cardio_count":     len(self._cardio_rows),
        }

    # ------------------------------------------------------------------
    # Carregamento de rotina
    # ------------------------------------------------------------------

    def load_routine(self, routine: Routine, session_id: int):
        self._session_id  = session_id
        exercises_with_sets = self._rm.get_routine_exercises(routine.id)
        self._exercises   = [ex for ex, _ in exercises_with_sets]  # Extrai apenas os exercícios
        self._current_idx = 0
        self._cardio_rows = []
        # Limpa cardio container
        while self._cardio_container.count():
            item = self._cardio_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._no_cardio_lbl.setVisible(True)

        self._title.setText(routine.name.upper())
        # Cria séries baseado no default_sets de cada exercício
        self._series_data = [
            [{"weight": "", "reps": "", "set_type": "N", "done": False, "saved": False} for _ in range(num_sets)]
            for _, num_sets in exercises_with_sets
        ]
        self._build_all_exercises()

    # ------------------------------------------------------------------
    # Exercícios
    # ------------------------------------------------------------------

    def _build_all_exercises(self):
        """Cria cards para todos os exercícios, um embaixo do outro."""
        # Limpa container
        while self._exercises_container.count():
            item = self._exercises_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Cria um card para cada exercício
        for ex_idx, ex in enumerate(self._exercises):
            card = self._create_exercise_card(ex_idx, ex)
            self._exercises_container.addWidget(card)

    def _create_exercise_card(self, ex_idx: int, ex: Exercise) -> QFrame:
        """Cria um card completo para um exercício."""
        card = QFrame()
        card.setObjectName("card")
        neon_glow(card, C_GREEN, blur=81, opacity=405)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(20, 20, 20, 20)
        card_lay.setSpacing(14)

        # Header do card
        card_hdr = QHBoxLayout()
        ex_icon = QLabel("◈")
        ex_icon.setFixedSize(44, 44)
        ex_icon.setAlignment(Qt.AlignCenter)
        ex_icon.setStyleSheet(f"background:{C_GREEN_BG}; border-radius:{RADIUS_MD}px; font-size:20px;")
        card_hdr.addWidget(ex_icon)
        card_hdr.addSpacing(12)

        card_info = QVBoxLayout()
        card_info.setSpacing(2)
        ex_name_lbl = label(ex.canonical_name.upper(), "h2")
        card_info.addWidget(ex_name_lbl)
        card_hdr.addLayout(card_info)
        card_hdr.addStretch()
        
        series = self._series_data[ex_idx]
        done = sum(1 for s in series if s["done"])
        ex_prog_lbl = QLabel(f"{done}/{len(series)}")
        ex_prog_lbl.setStyleSheet(f"color:{C_GREEN}; font-size:18px; font-weight:800; font-family:'Arial';")
        ex_prog_lbl.setObjectName(f"prog_{ex_idx}")  # Para atualizar depois
        card_hdr.addWidget(ex_prog_lbl)
        card_lay.addLayout(card_hdr)

        # Cabeçalho das séries
        s_hdr = QHBoxLayout()
        for txt, stretch in [("Série", 1), ("Peso (kg)", 4), ("Reps", 4), ("", 1)]:
            s_hdr.addWidget(label(txt, "sub"), stretch)
        card_lay.addLayout(s_hdr)

        # Séries
        series_layout = QVBoxLayout()
        series_layout.setSpacing(16)
        
        for s_idx, s in enumerate(series):
            row_w = QWidget()
            row_w.setStyleSheet(f"""
                QWidget {{ background: transparent; }}
                QLineEdit {{
                    background: transparent;
                    color: {C_TEXT};
                    border: none;
                    border-bottom: 1px solid {C_BORDER};
                    border-radius: 0px;
                    padding: 10px 8px;
                    font-size: 15px;
                }}
                QLineEdit:focus {{ 
                    border-bottom: 2px solid {C_GREEN};
                    background: transparent;
                }}
            """)
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(16)

            # Número da série em verde neon
            num = QLabel(str(s_idx + 1))
            num.setFixedWidth(40)
            num.setAlignment(Qt.AlignCenter)
            num.setStyleSheet(f"""
                color: {C_GREEN};
                font-size: 20px;
                font-weight: 900;
                font-family: 'Arial';
            """)
            row_lay.addWidget(num, 0)

            w_edit = QLineEdit(s["weight"])
            w_edit.setPlaceholderText("0")
            w_edit.setAlignment(Qt.AlignLeft)
            w_edit.setFixedHeight(44)
            w_edit.textChanged.connect(lambda v, i=ex_idx, j=s_idx: self._update(i, j, "weight", v))
            row_lay.addWidget(w_edit, 5)

            r_edit = QLineEdit(s["reps"])
            r_edit.setPlaceholderText("10-12")
            r_edit.setAlignment(Qt.AlignLeft)
            r_edit.setFixedHeight(44)
            r_edit.textChanged.connect(lambda v, i=ex_idx, j=s_idx: self._update(i, j, "reps", v))
            row_lay.addWidget(r_edit, 5)

            check = QPushButton()
            check.setFixedSize(52, 52)
            check.setCheckable(True)
            check.setChecked(s["done"])
            self._style_check(check, s["done"])
            
            # Função auxiliar para capturar os parâmetros corretamente
            def make_toggle_handler(ex_i, set_i, btn, prog, w_ed, r_ed):
                return lambda checked: self._toggle_done(ex_i, set_i, checked, btn, prog, w_ed, r_ed)
            
            check.clicked.connect(make_toggle_handler(ex_idx, s_idx, check, ex_prog_lbl, w_edit, r_edit))
            row_lay.addWidget(check, 0)

            series_layout.addWidget(row_w)
        
        card_lay.addLayout(series_layout)

        return card

    def _style_check(self, btn: QPushButton, done: bool):
        if done:
            btn.setIcon(qta.icon("fa5s.check", color="#000000"))
            btn.setStyleSheet(f"background:{C_GREEN}; border-radius:{RADIUS_MD}px; border:none;")
        else:
            btn.setIcon(qta.icon("fa5s.check", color=C_TEXT3))
            btn.setStyleSheet(f"background:{C_CARD2}; border-radius:{RADIUS_MD}px; border:1px solid {C_BORDER};")

    def _update(self, ex_idx: int, s_idx: int, key: str, val: str):
        self._series_data[ex_idx][s_idx][key] = val

    def _toggle_done(self, ex_idx: int, s_idx: int, checked: bool, btn: QPushButton, prog_lbl: QLabel, weight_edit: QLineEdit, reps_edit: QLineEdit):
        # Validação: verifica se peso e reps estão preenchidos
        if checked:
            weight_val = weight_edit.text().strip()
            reps_val = reps_edit.text().strip()
            
            # Verifica se os campos estão vazios
            if not weight_val or not reps_val:
                # Desmarca o botão
                btn.setChecked(False)
                
                # Destaca os campos vazios com borda vermelha
                if not weight_val:
                    weight_edit.setStyleSheet(f"""
                        background: transparent;
                        color: {C_TEXT};
                        border: none;
                        border-bottom: 2px solid #ef4444;
                        border-radius: 0px;
                        padding: 10px 8px;
                        font-size: 15px;
                    """)
                
                if not reps_val:
                    reps_edit.setStyleSheet(f"""
                        background: transparent;
                        color: {C_TEXT};
                        border: none;
                        border-bottom: 2px solid #ef4444;
                        border-radius: 0px;
                        padding: 10px 8px;
                        font-size: 15px;
                    """)
                
                # Mostra mensagem de erro
                from PySide6.QtWidgets import QMessageBox
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Campos obrigatórios")
                msg.setText("Você deve preencher o peso e as repetições antes de marcar a série como concluída.")
                msg.setStyleSheet(f"""
                    QMessageBox {{
                        background: {C_BG};
                        color: {C_TEXT};
                    }}
                    QPushButton {{
                        background: {C_GREEN};
                        color: #000;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 16px;
                        font-weight: 700;
                    }}
                    QPushButton:hover {{
                        background: #b8ff33;
                    }}
                """)
                msg.exec()
                return
        
        # Remove destaque vermelho se estava presente
        weight_edit.setStyleSheet(f"""
            background: transparent;
            color: {C_TEXT};
            border: none;
            border-bottom: 1px solid {C_BORDER};
            border-radius: 0px;
            padding: 10px 8px;
            font-size: 15px;
        """)
        reps_edit.setStyleSheet(f"""
            background: transparent;
            color: {C_TEXT};
            border: none;
            border-bottom: 1px solid {C_BORDER};
            border-radius: 0px;
            padding: 10px 8px;
            font-size: 15px;
        """)
        
        self._series_data[ex_idx][s_idx]["done"] = checked
        self._style_check(btn, checked)
        series = self._series_data[ex_idx]
        done = sum(1 for s in series if s["done"])
        prog_lbl.setText(f"{done}/{len(series)}")
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
                    self._series_data[ex_idx][s_idx]["saved"] = True
            except Exception as e:
                print(f"[GYMNight] Erro ao salvar série ex={ex_idx} s={s_idx}: {e} | dados={s}")

    def _update_progress(self):
        total = sum(len(s) for s in self._series_data)
        done  = sum(sum(1 for x in s if x["done"]) for s in self._series_data)
        self._series_counter.setText(f"{done}/{total} séries")
        if total > 0:
            QTimer.singleShot(0, lambda: self._prog_fill.setFixedWidth(
                int(self._prog_bar.width() * done / total)
            ))

    # ------------------------------------------------------------------
    # Finalização
    # ------------------------------------------------------------------

    def _build_summary_page(self) -> QWidget:
        """Tela de resumo exibida ao finalizar o treino (inline)."""
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setSpacing(24)
        lay.setAlignment(Qt.AlignTop)

        # Ícone de troféu
        icon_lbl = QLabel("🏆")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 64px;")
        lay.addWidget(icon_lbl)

        self._summary_title = label("TREINO CONCLUÍDO!", "h1")
        self._summary_title.setAlignment(Qt.AlignCenter)
        self._summary_title.setStyleSheet(f"color: {C_GREEN}; font-size: 28px; font-weight: 900;")
        lay.addWidget(self._summary_title)

        lay.addWidget(separator())

        # Cards de métricas
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(16)

        self._sum_volume = self._metric_card("Volume", "0 kg", "fa5s.dumbbell")
        self._sum_duration = self._metric_card("Duração", "00:00", "fa5s.clock")
        self._sum_cardio = self._metric_card("Cardio", "0 min", "fa5s.heartbeat")
        metrics_row.addWidget(self._sum_volume)
        metrics_row.addWidget(self._sum_duration)
        metrics_row.addWidget(self._sum_cardio)
        lay.addLayout(metrics_row)

        self._sum_cardio_pse_lbl = label("", "sub")
        self._sum_cardio_pse_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._sum_cardio_pse_lbl)

        # ── Muscle heatmap ────────────────────────────────────────────────
        lay.addWidget(separator())
        heatmap_title = label("MÚSCULOS TRABALHADOS", "h3")
        heatmap_title.setAlignment(Qt.AlignCenter)
        lay.addWidget(heatmap_title)

        self._heatmap = MuscleHeatmapWidget()
        lay.addWidget(self._heatmap)

        lay.addStretch()

        # Botão voltar para treinos
        btn_done = QPushButton(" Voltar para Treinos")
        btn_done.setIcon(qta.icon("fa5s.home", color="#000000"))
        btn_done.setMinimumHeight(48)
        btn_done.setStyleSheet(f"""
            QPushButton {{
                background: {C_GREEN};
                color: #000;
                border: none;
                border-radius: {RADIUS_MD}px;
                font-size: 15px;
                font-weight: 700;
                padding: 0 24px;
            }}
            QPushButton:hover {{ background: #bef264; }}
        """)
        btn_done.clicked.connect(self._on_summary_done)
        lay.addWidget(btn_done)

        scroll.setWidget(content)
        root.addWidget(scroll)
        return page

    def _metric_card(self, title: str, value: str, icon_name: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        neon_glow(card, C_GREEN, blur=68, opacity=324)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(16, 16, 16, 16)
        card_lay.setSpacing(8)
        card_lay.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_name, color=C_GREEN).pixmap(28, 28))
        icon_lbl.setAlignment(Qt.AlignCenter)
        card_lay.addWidget(icon_lbl)

        val_lbl = QLabel(value)
        val_lbl.setAlignment(Qt.AlignCenter)
        val_lbl.setStyleSheet(f"color: {C_TEXT}; font-size: 22px; font-weight: 800;")
        card_lay.addWidget(val_lbl)

        title_lbl = label(title, "sub")
        title_lbl.setAlignment(Qt.AlignCenter)
        card_lay.addWidget(title_lbl)

        # Guarda referência ao label de valor para atualizar depois
        card._value_lbl = val_lbl
        return card

    def _finish(self):
        # Salva cardio no banco
        self._save_cardio_logs()

        duration = self._rm.end_session(self._session_id) if self._session_id else 0

        # Salva séries que têm dados mas não foram salvas ainda
        if self._session_id:
            for ex_idx, ex_series in enumerate(self._series_data):
                for s_idx, s in enumerate(ex_series):
                    if s.get("saved"):
                        continue
                    try:
                        w = float(s["weight"]) if s["weight"] else 0.0
                        r = int(s["reps"]) if s["reps"] else 0
                        if w > 0 and r > 0:
                            self._db.execute_write(
                                "INSERT INTO workout_logs (exercise_id, session_id, weight_kg, reps, set_type) VALUES (?,?,?,?,?)",
                                (self._exercises[ex_idx].id, self._session_id, w, r, s.get("set_type", "N")),
                            )
                    except Exception as e:
                        print(f"[GYMNight] Erro ao salvar série no finish ex={ex_idx} s={s_idx}: {e}")

        done_series = [(i, j, s) for i, ex in enumerate(self._series_data)
                       for j, s in enumerate(ex) if s.get("done")]
        print(f"[GYMNight] Séries marcadas como done: {len(done_series)}")

        logs_count = self._db.fetchone(
            "SELECT COUNT(*) AS c FROM workout_logs WHERE session_id=?", (self._session_id,)
        )
        print(f"[GYMNight] Registros no banco para session_id={self._session_id}: {logs_count['c'] if logs_count else 0}")

        row = self._db.fetchone(
            "SELECT COALESCE(SUM(weight_kg*reps),0) AS v FROM workout_logs WHERE session_id=?",
            (self._session_id,),
        )
        vol = float(row["v"]) if row else 0.0
        cardio = self._cardio_summary()
        mins, secs = divmod(duration, 60)

        # Atualiza tela de resumo
        self._sum_volume._value_lbl.setText(f"{vol:.0f} kg")
        self._sum_duration._value_lbl.setText(f"{mins:02d}:{secs:02d}")
        if cardio["cardio_count"] > 0:
            self._sum_cardio._value_lbl.setText(f"{int(cardio['cardio_total_min'])} min")
            pse_txt = f"PSE médio: {cardio['cardio_avg_pse']}/10" if cardio["cardio_avg_pse"] else ""
            self._sum_cardio_pse_lbl.setText(pse_txt)
        else:
            self._sum_cardio._value_lbl.setText("—")
            self._sum_cardio_pse_lbl.setText("")

        # Atualiza heatmap muscular — session_id ainda válido aqui
        if self._session_id:
            breakdown = self._analyzer.get_muscle_volume_breakdown(self._session_id)
            muscle_vols = {r.muscle_group_id: r.volume for r in breakdown}
        else:
            muscle_vols = {}
        self._heatmap.update_heatmap(muscle_vols)

        self._finish_payload = {
            "session_id":       self._session_id,
            "volume_total":     vol,
            "duration_seconds": duration,
            "routine_name":     self._title.text(),
            **cardio,
        }
        self._session_id = None

        # Mostra tela de resumo inline
        self._main_stack.setCurrentIndex(1)

    def _on_summary_done(self):
        """Volta para a lista de treinos após ver o resumo."""
        self._main_stack.setCurrentIndex(0)
        self.finished.emit(self._finish_payload)

    def _confirm_back(self):
        if QMessageBox.question(self, "Voltar", "Abandonar o treino atual?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self._session_id = None
            self._main_stack.setCurrentIndex(0)
            self.finished.emit({})
