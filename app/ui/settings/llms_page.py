from PySide6 import QtWidgets, QtCore
from ..dayu_widgets.label import MLabel
from ..dayu_widgets.text_edit import MTextEdit
from ..dayu_widgets.check_box import MCheckBox
from ..dayu_widgets.collapse import MCollapse
from ..dayu_widgets.combo_box import MComboBox
from ..dayu_widgets.divider import MDivider
from ..dayu_widgets.line_edit import MLineEdit
from ..dayu_widgets.push_button import MPushButton


class LlmsPage(QtWidgets.QWidget):
    DEFAULT_EXTRA_CONTEXT_LIMIT = 1000
    NO_PRESET_LABEL = "—"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._extra_context_limit: int | None = self.DEFAULT_EXTRA_CONTEXT_LIMIT
        # name -> instructions text
        self._prompt_presets: dict[str, str] = {}
        # Hosted (ComicLabs account) translation runs server-side and has no
        # channel for custom system instructions, so the section gets disabled.
        self._custom_prompt_supported = True

        v = QtWidgets.QVBoxLayout(self)
        main_layout = QtWidgets.QHBoxLayout()

        self.image_checkbox = MCheckBox(self.tr("Provide Image as Input to AI"))
        self.image_checkbox.setChecked(False)

        # Left
        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(MDivider(self.tr("Extra Context")))
        prompt_label = MLabel(self.tr("Extra Context:"))
        extra_context_hint = MLabel(
            self.tr(
                "Added to the user message of every translation request "
                "(story background, character notes, etc.)."
            )
        ).secondary()
        extra_context_hint.setWordWrap(True)
        self.extra_context = MTextEdit()
        self.extra_context.setMinimumHeight(200)
        left_layout.addWidget(prompt_label)
        left_layout.addWidget(extra_context_hint)
        left_layout.addWidget(self.extra_context)
        left_layout.addWidget(self.image_checkbox)
        left_layout.addStretch(1)

        # Right
        right_layout = QtWidgets.QVBoxLayout()
        self._build_custom_system_prompt_section(right_layout)
        right_layout.addSpacing(10)
        right_layout.addStretch(1)

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 1)

        v.addLayout(main_layout)
        v.addStretch(1)

        self.extra_context.textChanged.connect(self._limit_extra_context)

    # ------------------------------------------------------------------
    # Custom system prompt
    # ------------------------------------------------------------------
    def _build_custom_system_prompt_section(self, layout: QtWidgets.QVBoxLayout) -> None:
        layout.addWidget(MDivider(self.tr("Custom System Prompt")))

        self.enable_custom_system_prompt = MCheckBox(
            self.tr("Append custom instructions to the system prompt")
        )
        self.enable_custom_system_prompt.setChecked(False)
        layout.addWidget(self.enable_custom_system_prompt)

        description = MLabel(
            self.tr(
                "This text is appended to the base system prompt and controls how the model "
                "translates: tone, level of formality, specific terminology, and style rules. "
                "The base prompt itself is never replaced."
            )
        ).secondary()
        description.setWordWrap(True)
        layout.addWidget(description)

        # Shown when the selected engine can't carry custom system instructions
        # (hosted ComicLabs account mode).
        self.custom_prompt_notice = MLabel("").warning()
        self.custom_prompt_notice.setWordWrap(True)
        self.custom_prompt_notice.setVisible(False)
        layout.addWidget(self.custom_prompt_notice)

        # Preset row
        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(MLabel(self.tr("Preset:")))
        self.prompt_preset_combo = MComboBox().small()
        self.prompt_preset_combo.setMinimumWidth(140)
        preset_row.addWidget(self.prompt_preset_combo, 1)

        self.save_preset_button = MPushButton(self.tr("Save")).small()
        self.delete_preset_button = MPushButton(self.tr("Delete")).small()
        preset_row.addWidget(self.save_preset_button)
        preset_row.addWidget(self.delete_preset_button)
        layout.addLayout(preset_row)

        self.preset_name_input = MLineEdit().small()
        self.preset_name_input.setPlaceholderText(
            self.tr("Preset name (e.g. formal, colloquial, humorous)")
        )
        layout.addWidget(self.preset_name_input)

        self.custom_system_instructions = MTextEdit()
        self.custom_system_instructions.setMinimumHeight(200)
        self.custom_system_instructions.setPlaceholderText(
            self.tr(
                "e.g. Keep honorifics untranslated. Use a formal register. "
                "Always translate 'Nen' as 'Nen'."
            )
        )
        layout.addWidget(self.custom_system_instructions)

        self._refresh_preset_combo()
        self._sync_custom_prompt_enabled_state()

        self.enable_custom_system_prompt.toggled.connect(
            lambda _=None: self._sync_custom_prompt_enabled_state()
        )
        self.prompt_preset_combo.currentTextChanged.connect(self._on_preset_selected)
        self.save_preset_button.clicked.connect(self._on_save_preset)
        self.delete_preset_button.clicked.connect(self._on_delete_preset)

    def set_custom_system_prompt_supported(self, supported: bool, reason: str = "") -> None:
        """Enable/disable the whole section depending on the active engine.

        Translation through a signed-in ComicLabs account is performed by the
        web API, which accepts no custom system instructions, so the field is
        greyed out with an explanation instead of being silently ignored.
        """
        self._custom_prompt_supported = bool(supported)
        self.custom_prompt_notice.setText(reason or "")
        self.custom_prompt_notice.setVisible(bool(reason) and not supported)
        self._sync_custom_prompt_enabled_state()

    def _sync_custom_prompt_enabled_state(self) -> None:
        supported = self._custom_prompt_supported
        self.enable_custom_system_prompt.setEnabled(supported)
        enabled = supported and self.enable_custom_system_prompt.isChecked()
        for widget in (
            self.custom_system_instructions,
            self.prompt_preset_combo,
            self.preset_name_input,
            self.save_preset_button,
            self.delete_preset_button,
        ):
            widget.setEnabled(enabled)

    def get_prompt_presets(self) -> dict[str, str]:
        """Named custom-prompt presets, as a plain dict (safe to serialize)."""
        return dict(self._prompt_presets)

    def set_prompt_presets(self, presets: dict) -> None:
        """Replace the preset library. Invalid entries are ignored."""
        cleaned: dict[str, str] = {}
        if isinstance(presets, dict):
            for name, text in presets.items():
                if isinstance(name, str) and name.strip() and isinstance(text, str):
                    cleaned[name.strip()] = text
        self._prompt_presets = cleaned
        self._refresh_preset_combo()

    def _refresh_preset_combo(self, select: str = "") -> None:
        combo = self.prompt_preset_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItems([self.NO_PRESET_LABEL, *sorted(self._prompt_presets)])
        if select and combo.findText(select) != -1:
            combo.setCurrentText(select)
        else:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _on_preset_selected(self, name: str) -> None:
        if not name or name == self.NO_PRESET_LABEL:
            return
        text = self._prompt_presets.get(name)
        if text is None:
            return
        self.custom_system_instructions.setPlainText(text)
        self.preset_name_input.setText(name)

    def _on_save_preset(self) -> None:
        name = self.preset_name_input.text().strip()
        if not name:
            name = self.prompt_preset_combo.currentText().strip()
        if not name or name == self.NO_PRESET_LABEL:
            self.preset_name_input.setFocus()
            return
        self._prompt_presets[name] = self.custom_system_instructions.toPlainText()
        self._refresh_preset_combo(select=name)

    def _on_delete_preset(self) -> None:
        name = self.prompt_preset_combo.currentText().strip()
        if not name or name == self.NO_PRESET_LABEL:
            return
        self._prompt_presets.pop(name, None)
        self.preset_name_input.clear()
        self._refresh_preset_combo()

    def set_extra_context_unlimited(self, enabled: bool) -> None:
        self._extra_context_limit = None if enabled else self.DEFAULT_EXTRA_CONTEXT_LIMIT
        self._limit_extra_context()

    def _limit_extra_context(self):
        max_length = self._extra_context_limit
        if max_length is None:
            return
        text = self.extra_context.toPlainText()
        if len(text) > max_length:
            # Preserve cursor position
            cursor = self.extra_context.textCursor()
            position = cursor.position()
            
            # Truncate
            self.extra_context.setPlainText(text[:max_length])
            
            # Restore cursor (clamped to end)
            new_position = min(position, max_length)
            cursor.setPosition(new_position)
            self.extra_context.setTextCursor(cursor)

