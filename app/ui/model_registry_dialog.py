"""Model registry dialog: edit the LLM / OCR model map.

The map is stored in ``<user data dir>/models/models.json`` (see
``modules/utils/model_registry``). Edits apply on the next run — the
translation engines snapshot the map at import time — which the dialog says
explicitly. Built-in entries can be renamed/remapped but the defaults always
come back, so the app can never end up with an empty map.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6 import QtCore, QtWidgets

from .dayu_widgets.label import MLabel
from .dayu_widgets.line_edit import MLineEdit
from .dayu_widgets.push_button import MPushButton
from .dayu_widgets.combo_box import MComboBox
from .dayu_widgets import dayu_theme

if TYPE_CHECKING:
    from controller import ComicTranslate

COLUMN_KEY = 0
COLUMN_API_MODEL = 1


class ModelRegistryDialog(QtWidgets.QDialog):
    sig_saved = QtCore.Signal()

    def __init__(self, main: "ComicTranslate", parent=None):
        super().__init__(parent)
        self.main = main
        self.setWindowTitle(self.tr("Model Registry"))
        self.setMinimumSize(640, 520)

        from modules.utils.model_registry import get_registry_data

        self._data = get_registry_data()
        self._build_ui()
        self._reload_tables()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        hint = MLabel(
            self.tr(
                "Map the app's model names to the model IDs your provider accepts. "
                "Newer models can be added without waiting for an app update. "
                "Changes apply to the next translation run. The built-in defaults "
                "can never be deleted — they come back automatically."
            )
        ).secondary()
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.tab_widget = QtWidgets.QTabWidget()
        self.llm_table = self._build_table_widget()
        self.ocr_table = self._build_table_widget()
        self.tab_widget.addTab(self.llm_table, self.tr("Translator (LLM) models"))
        self.tab_widget.addTab(self.ocr_table, self.tr("OCR models"))
        layout.addWidget(self.tab_widget, 1)

        self._build_network_row(layout)

        layout.addWidget(
            MLabel(
                self.tr(
                    "When a ComicLabs account is signed in, translation and OCR run on the "
                    "server and this local registry is not consulted."
                )
            ).secondary()
        )

        buttons = QtWidgets.QHBoxLayout()
        self.add_button = MPushButton(self.tr("Add Row")).small()
        self.remove_button = MPushButton(self.tr("Remove Selected")).small()
        self.restore_button = MPushButton(self.tr("Restore Defaults")).small()
        self.save_button = MPushButton(self.tr("Save")).small()
        close_button = MPushButton(self.tr("Close")).small()

        self.add_button.clicked.connect(lambda: self._add_row(self._current_table()))
        self.remove_button.clicked.connect(self._remove_selected)
        self.restore_button.clicked.connect(self._restore_defaults)
        self.save_button.clicked.connect(self._on_save)

        for btn in (self.add_button, self.remove_button, self.restore_button):
            buttons.addWidget(btn)
        buttons.addStretch(1)
        buttons.addWidget(self.save_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        close_button.clicked.connect(self.accept)

    def _build_table_widget(self) -> QtWidgets.QTableWidget:
        table = QtWidgets.QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(
            [self.tr("App model name"), self.tr("API model ID")]
        )
        table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        return table

    def _build_network_row(self, layout: QtWidgets.QVBoxLayout) -> None:
        """Fetch-models / test-key row. All requests are lightweight lists."""
        row = QtWidgets.QHBoxLayout()
        row.addWidget(MLabel(self.tr("Provider:")))
        self.provider_combo = MComboBox().small()
        self.provider_combo.addItems(
            [self.tr("OpenAI-compatible"), self.tr("Google Gemini")]
        )
        row.addWidget(self.provider_combo)

        row.addWidget(MLabel(self.tr("API Key:")))
        self.key_input = MLineEdit().small()
        self.key_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.key_input.setMinimumWidth(180)
        row.addWidget(self.key_input, 1)

        self.test_key_button = MPushButton(self.tr("Test Key")).small()
        self.fetch_button = MPushButton(self.tr("Fetch Models")).small()
        row.addWidget(self.test_key_button)
        row.addWidget(self.fetch_button)
        layout.addLayout(row)

        self.network_status = MLabel("").secondary()
        self.network_status.setWordWrap(True)
        layout.addWidget(self.network_status)

        self.test_key_button.clicked.connect(self._on_test_key)
        self.fetch_button.clicked.connect(self._on_fetch_models)

    # ------------------------------------------------------------------
    # Table <-> data
    # ------------------------------------------------------------------
    def _current_section(self) -> str:
        return "llm" if self.tab_widget.currentIndex() == 0 else "ocr"

    def _current_table(self) -> QtWidgets.QTableWidget:
        return self.llm_table if self.tab_widget.currentIndex() == 0 else self.ocr_table

    def _reload_tables(self) -> None:
        for table, section in ((self.llm_table, "llm"), (self.ocr_table, "ocr")):
            table.setRowCount(0)
            for key, api_id in sorted(self._data.get(section, {}).items()):
                row = table.rowCount()
                table.insertRow(row)
                key_item = QtWidgets.QTableWidgetItem(key)
                api_item = QtWidgets.QTableWidgetItem(api_id or "")
                table.setItem(row, COLUMN_KEY, key_item)
                table.setItem(row, COLUMN_API_MODEL, api_item)
            table.sortItems(COLUMN_KEY, QtCore.Qt.SortOrder.AscendingOrder)

    def _collect_from_table(self, table: QtWidgets.QTableWidget) -> dict[str, str]:
        out: dict[str, str] = {}
        for row in range(table.rowCount()):
            key_item = table.item(row, COLUMN_KEY)
            api_item = table.item(row, COLUMN_API_MODEL)
            key = (key_item.text() if key_item else "").strip()
            api_id = api_item.text() if api_item else ""
            if key:
                out[key] = api_id
        return out

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _add_row(self, table: QtWidgets.QTableWidget) -> None:
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, COLUMN_KEY, QtWidgets.QTableWidgetItem(""))
        table.setItem(row, COLUMN_API_MODEL, QtWidgets.QTableWidgetItem(""))
        table.editItem(table.item(row, COLUMN_KEY))

    def _remove_selected(self) -> None:
        table = self._current_table()
        selected = table.selectionModel().selectedRows()
        for index in sorted(selected, key=lambda i: i.row(), reverse=True):
            table.removeRow(index.row())

    def _restore_defaults(self) -> None:
        section = self._current_section()
        from modules.utils.model_registry import _defaults_for

        self._data[section] = dict(_defaults_for(section))
        self._reload_tables()

    def _on_save(self) -> None:
        from modules.utils.model_registry import set_llm_models, set_ocr_models

        self._data["llm"] = self._collect_from_table(self.llm_table)
        self._data["ocr"] = self._collect_from_table(self.ocr_table)
        try:
            set_llm_models(self._data["llm"])
            set_ocr_models(self._data["ocr"])
        except OSError as exc:
            QtWidgets.QMessageBox.warning(
                self,
                self.tr("Could Not Save"),
                self.tr("The registry file could not be written:\n{error}").format(
                    error=str(exc)
                ),
            )
            return
        self.sig_saved.emit()
        self._reload_tables()

    def _on_test_key(self) -> None:
        from app.controllers.model_registry_ctrl import test_api_key

        provider = "gemini" if self.provider_combo.currentIndex() == 1 else "openai"
        ok, message = test_api_key(provider, self.key_input.text().strip())
        self.network_status.setText(message)
        self.network_status.setProperty("warning", not ok)
        self.network_status.style().unpolish(self.network_status)
        self.network_status.style().polish(self.network_status)

    def _on_fetch_models(self) -> None:
        from app.controllers.model_registry_ctrl import fetch_models, friendly_llm_key

        provider = "gemini" if self.provider_combo.currentIndex() == 1 else "openai"
        ok, ids, message = fetch_models(provider, self.key_input.text().strip())
        self.network_status.setText(message)
        self.network_status.setProperty("warning", not ok)
        self.network_status.style().unpolish(self.network_status)
        self.network_status.style().polish(self.network_status)
        if not ok or not ids:
            return

        section = self._current_section()
        existing_keys = {k.lower() for k in self._data.get(section, {})}
        existing_ids = {v.lower() for v in self._data.get(section, {}).values()}
        added = 0
        for api_id in ids:
            if api_id.lower() in existing_ids:
                continue
            if section == "llm":
                key = friendly_llm_key(api_id)
            else:
                key = api_id
            if key and key.lower() not in existing_keys:
                self._data[section][key] = api_id
                existing_keys.add(key.lower())
                existing_ids.add(api_id.lower())
                added += 1
        self._reload_tables()
        if added:
            self.network_status.setText(
                message + self.tr(" Added {n} new model(s).").format(n=added)
            )

    def accept(self) -> None:
        super().accept()
