"""
ui/widgets/muscle_heatmap.py
Renders front + back human body SVGs with HSL heat-map coloring per muscle group.
"""
from __future__ import annotations

import re

from PySide6.QtCore import Qt, QByteArray
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.ui.theme import C_TEXT3

# ---------------------------------------------------------------------------
# Muscle group ID → SVG element IDs
# muscle_groups table: 1=chest 2=back 3=shoulders 4=biceps 5=triceps 6=legs 7=abs
# ---------------------------------------------------------------------------
_MUSCLE_SVG_IDS: dict[int, list[str]] = {
    1: ["chest_l", "chest_r"],
    2: ["back_upper_l", "back_upper_r", "back_lower_l", "back_lower_r"],
    3: ["shoulder_l", "shoulder_r", "shoulder_back_l", "shoulder_back_r"],
    4: ["bicep_l", "bicep_r"],
    5: ["tricep_l", "tricep_r"],
    6: ["quad_l", "quad_r", "hamstring_l", "hamstring_r",
        "glute_l", "glute_r", "calf_l", "calf_r"],
    7: ["abs"],
}

_NEUTRAL = "#1E1E1E"


def _hsl_color(activation: float, max_activation: float) -> str:
    """HSL hue=120 (neon green), sat=100%, lightness scales with activation."""
    if max_activation <= 0 or activation <= 0:
        return _NEUTRAL
    lightness = (activation / max_activation) * 0.80 + 0.10
    return f"hsl(210, 100%, {lightness * 100:.1f}%)"


def _apply_colors(svg: str, id_color: dict[str, str]) -> str:
    """
    For each element id, find the tag that contains it and replace its fill.
    Uses regex so it works regardless of attribute order or line breaks.
    """
    for elem_id, color in id_color.items():
        # Match any opening SVG tag that contains id="elem_id"
        # Then replace (or insert) the fill attribute within that tag
        def replacer(m: re.Match, _color: str = color) -> str:
            tag = m.group(0)
            if 'fill=' in tag:
                # Replace existing fill value
                tag = re.sub(r'fill="[^"]*"', f'fill="{_color}"', tag)
            else:
                # Insert fill before the closing > or />
                tag = re.sub(r'(/?>)', f' fill="{_color}"\\1', tag, count=1)
            return tag

        # Match the opening tag (not closing) that has this id
        pattern = rf'<[^/][^>]*\bid="{re.escape(elem_id)}"[^>]*/?>'
        svg = re.sub(pattern, replacer, svg, flags=re.DOTALL)

    return svg


def _build_colored_svg(base_svg: str, muscle_volumes: dict[int, float]) -> str:
    """Return SVG string with muscle fills replaced according to volumes."""
    max_vol = max(muscle_volumes.values(), default=0.0)

    id_color: dict[str, str] = {}
    for mg_id, svg_ids in _MUSCLE_SVG_IDS.items():
        vol = muscle_volumes.get(mg_id, 0.0)
        color = _hsl_color(vol, max_vol)
        for sid in svg_ids:
            id_color[sid] = color

    return _apply_colors(base_svg, id_color)


# ---------------------------------------------------------------------------
# Widget
# ---------------------------------------------------------------------------

class MuscleHeatmapWidget(QWidget):
    """
    Displays front + back body SVGs with muscle heat-map.
    Call update_heatmap({muscle_group_id: volume}) to refresh.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(24)

        def _labeled(svg_widget: QSvgWidget, text: str) -> QWidget:
            w = QWidget()
            v = QVBoxLayout(w)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(4)
            v.addWidget(svg_widget)
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {C_TEXT3}; font-size: 11px; font-weight: 600;")
            v.addWidget(lbl)
            return w

        self._svg_front = QSvgWidget()
        self._svg_back  = QSvgWidget()
        for w in (self._svg_front, self._svg_back):
            w.setFixedSize(150, 300)
            w.setStyleSheet("background: transparent;")

        root.addStretch()
        root.addWidget(_labeled(self._svg_front, "FRENTE"))
        root.addWidget(_labeled(self._svg_back,  "COSTAS"))
        root.addStretch()

        self.update_heatmap({})

    def update_heatmap(self, muscle_volumes: dict[int, float]):
        front = _build_colored_svg(_SVG_FRONT, muscle_volumes)
        back  = _build_colored_svg(_SVG_BACK,  muscle_volumes)
        self._svg_front.load(QByteArray(front.encode("utf-8")))
        self._svg_back.load(QByteArray(back.encode("utf-8")))


# ---------------------------------------------------------------------------
# SVG definitions — two separate files, viewBox fits each figure
# Muscle elements carry id="<name>" and fill="#1E1E1E" as defaults.
# _apply_colors() will replace those fills at runtime.
# ---------------------------------------------------------------------------

_SVG_FRONT = """\
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 170 370" width="170" height="370">
  <defs>
    <style>
      .base   { stroke:#3a3a3a; stroke-width:1.0; }
      .muscle { stroke:#333333; stroke-width:0.7; }
    </style>
  </defs>

  <!-- Head -->
  <ellipse cx="85" cy="30" rx="20" ry="24" fill="#3a3a3a" class="base"/>
  <!-- Neck -->
  <rect x="79" y="52" width="12" height="14" rx="3" fill="#3a3a3a" class="base"/>

  <!-- Torso silhouette -->
  <path d="M52,66 Q85,60 118,66 L122,158 Q85,166 48,158 Z" fill="#252525" class="base"/>

  <!-- Chest L -->
  <path d="M55,72 Q70,68 83,72 L84,112 Q70,118 54,112 Z"
        id="chest_l" fill="#1E1E1E" class="muscle"/>
  <!-- Chest R -->
  <path d="M87,72 Q100,68 115,72 L116,112 Q100,118 86,112 Z"
        id="chest_r" fill="#1E1E1E" class="muscle"/>

  <!-- Abs -->
  <path d="M62,116 Q85,112 108,116 L110,156 Q85,162 60,156 Z"
        id="abs" fill="#1E1E1E" class="muscle"/>

  <!-- Shoulder L -->
  <ellipse cx="43" cy="82" rx="13" ry="17"
           id="shoulder_l" fill="#1E1E1E" class="muscle"/>
  <!-- Shoulder R -->
  <ellipse cx="127" cy="82" rx="13" ry="17"
           id="shoulder_r" fill="#1E1E1E" class="muscle"/>

  <!-- Bicep L -->
  <path d="M32,96 Q26,100 24,122 Q28,132 36,130 Q44,128 46,106 Z"
        id="bicep_l" fill="#1E1E1E" class="muscle"/>
  <!-- Bicep R -->
  <path d="M138,96 Q144,100 146,122 Q142,132 134,130 Q126,128 124,106 Z"
        id="bicep_r" fill="#1E1E1E" class="muscle"/>

  <!-- Forearm L -->
  <path d="M24,124 Q20,140 22,160 Q28,164 34,160 Q38,140 36,124 Z"
        fill="#2a2a2a" class="base"/>
  <!-- Forearm R -->
  <path d="M146,124 Q150,140 148,160 Q142,164 136,160 Q132,140 134,124 Z"
        fill="#2a2a2a" class="base"/>

  <!-- Hand L -->
  <ellipse cx="23" cy="168" rx="7" ry="9" fill="#2a2a2a" class="base"/>
  <!-- Hand R -->
  <ellipse cx="147" cy="168" rx="7" ry="9" fill="#2a2a2a" class="base"/>

  <!-- Hip -->
  <path d="M52,158 Q85,166 118,158 L120,184 Q85,192 50,184 Z"
        fill="#252525" class="base"/>

  <!-- Quad L -->
  <path d="M54,184 Q67,180 79,184 L80,246 Q66,252 52,246 Z"
        id="quad_l" fill="#1E1E1E" class="muscle"/>
  <!-- Quad R -->
  <path d="M91,184 Q103,180 116,184 L117,246 Q103,252 90,246 Z"
        id="quad_r" fill="#1E1E1E" class="muscle"/>

  <!-- Knee L -->
  <ellipse cx="66" cy="251" rx="12" ry="9" fill="#2a2a2a" class="base"/>
  <!-- Knee R -->
  <ellipse cx="104" cy="251" rx="12" ry="9" fill="#2a2a2a" class="base"/>

  <!-- Calf L -->
  <path d="M54,259 Q66,255 78,259 L78,308 Q66,312 54,308 Z"
        id="calf_l" fill="#1E1E1E" class="muscle"/>
  <!-- Calf R -->
  <path d="M92,259 Q104,255 116,259 L116,308 Q104,312 92,308 Z"
        id="calf_r" fill="#1E1E1E" class="muscle"/>

  <!-- Foot L -->
  <path d="M52,308 Q66,312 78,308 L76,320 Q62,326 50,320 Z"
        fill="#2a2a2a" class="base"/>
  <!-- Foot R -->
  <path d="M92,308 Q104,312 118,308 L120,320 Q106,326 90,320 Z"
        fill="#2a2a2a" class="base"/>
</svg>"""


_SVG_BACK = """\
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 170 370" width="170" height="370">
  <defs>
    <style>
      .base   { stroke:#3a3a3a; stroke-width:1.0; }
      .muscle { stroke:#333333; stroke-width:0.7; }
    </style>
  </defs>

  <!-- Head -->
  <ellipse cx="85" cy="30" rx="20" ry="24" fill="#3a3a3a" class="base"/>
  <!-- Neck -->
  <rect x="79" y="52" width="12" height="14" rx="3" fill="#3a3a3a" class="base"/>

  <!-- Torso silhouette -->
  <path d="M52,66 Q85,60 118,66 L122,158 Q85,166 48,158 Z" fill="#252525" class="base"/>

  <!-- Upper back L (traps + lats) -->
  <path d="M55,70 Q70,66 83,72 L83,128 Q68,134 54,126 Z"
        id="back_upper_l" fill="#1E1E1E" class="muscle"/>
  <!-- Upper back R -->
  <path d="M87,72 Q100,66 115,70 L116,126 Q102,134 87,128 Z"
        id="back_upper_r" fill="#1E1E1E" class="muscle"/>

  <!-- Lower back L -->
  <path d="M55,128 Q69,124 83,128 L83,156 Q69,162 54,156 Z"
        id="back_lower_l" fill="#1E1E1E" class="muscle"/>
  <!-- Lower back R -->
  <path d="M87,128 Q101,124 115,128 L115,156 Q101,162 87,156 Z"
        id="back_lower_r" fill="#1E1E1E" class="muscle"/>

  <!-- Shoulder back L -->
  <ellipse cx="43" cy="82" rx="13" ry="17"
           id="shoulder_back_l" fill="#1E1E1E" class="muscle"/>
  <!-- Shoulder back R -->
  <ellipse cx="127" cy="82" rx="13" ry="17"
           id="shoulder_back_r" fill="#1E1E1E" class="muscle"/>

  <!-- Tricep L -->
  <path d="M32,96 Q26,100 24,122 Q28,132 36,130 Q44,128 46,106 Z"
        id="tricep_l" fill="#1E1E1E" class="muscle"/>
  <!-- Tricep R -->
  <path d="M138,96 Q144,100 146,122 Q142,132 134,130 Q126,128 124,106 Z"
        id="tricep_r" fill="#1E1E1E" class="muscle"/>

  <!-- Forearm L -->
  <path d="M24,124 Q20,140 22,160 Q28,164 34,160 Q38,140 36,124 Z"
        fill="#2a2a2a" class="base"/>
  <!-- Forearm R -->
  <path d="M146,124 Q150,140 148,160 Q142,164 136,160 Q132,140 134,124 Z"
        fill="#2a2a2a" class="base"/>

  <!-- Hand L -->
  <ellipse cx="23" cy="168" rx="7" ry="9" fill="#2a2a2a" class="base"/>
  <!-- Hand R -->
  <ellipse cx="147" cy="168" rx="7" ry="9" fill="#2a2a2a" class="base"/>

  <!-- Glute L -->
  <path d="M52,158 Q67,154 81,160 L81,194 Q67,200 52,194 Z"
        id="glute_l" fill="#1E1E1E" class="muscle"/>
  <!-- Glute R -->
  <path d="M89,160 Q103,154 118,158 L118,194 Q103,200 89,194 Z"
        id="glute_r" fill="#1E1E1E" class="muscle"/>

  <!-- Hamstring L -->
  <path d="M54,194 Q67,190 79,194 L79,246 Q65,252 52,246 Z"
        id="hamstring_l" fill="#1E1E1E" class="muscle"/>
  <!-- Hamstring R -->
  <path d="M91,194 Q103,190 116,194 L116,246 Q103,252 90,246 Z"
        id="hamstring_r" fill="#1E1E1E" class="muscle"/>

  <!-- Knee L -->
  <ellipse cx="66" cy="251" rx="12" ry="9" fill="#2a2a2a" class="base"/>
  <!-- Knee R -->
  <ellipse cx="104" cy="251" rx="12" ry="9" fill="#2a2a2a" class="base"/>

  <!-- Calf back L -->
  <path d="M54,259 Q66,255 78,259 L78,308 Q66,312 54,308 Z"
        fill="#2a2a2a" class="base"/>
  <!-- Calf back R -->
  <path d="M92,259 Q104,255 116,259 L116,308 Q104,312 92,308 Z"
        fill="#2a2a2a" class="base"/>

  <!-- Foot L -->
  <path d="M52,308 Q66,312 78,308 L76,320 Q62,326 50,320 Z"
        fill="#2a2a2a" class="base"/>
  <!-- Foot R -->
  <path d="M92,308 Q104,312 118,308 L120,320 Q106,326 90,320 Z"
        fill="#2a2a2a" class="base"/>
</svg>"""
