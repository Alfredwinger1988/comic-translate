"""Project glossary dialog: manage the term -> translation table of a project.

The table is saved into the project file (see ``project_state_v2``) and fed to
the translator as extra context, so it is a per-project document, not a global
preference.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtWidgets

from ..dayu_widgets.label import MLabel
from ..dayu_widgets.line_edit import MLineEdit
from ..dayu_widgets.push_button import MPushButton
from ..dayu_widgets.divider import MDivider
from ..dayu_widgets import dayu_theme

if TYPE_CHECKING:
    from controller import ComicTranslate

COLUMN_TERM = 0
COLUMN_TRANSLATION = 1


class GlossaryDialog(QtWidgets.QDialog):
    """Editable term table backed by the controller's GlossaryStore.

    Edits write straight into the store; the dialog only manages the visual
    table plus add/remove/load/save.
    """

    def __init__(self, main: "ComicTranslate", parent=None):
        super().__init__(parent)
        self.main = main
        self._store = main.glossary_store
        self.setWindowTitle(self.tr("Project Glossary"))
        self.setMinimumSize(560, 420)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        hint = MLabel(
            self.tr(
                "Terms here are sent to the translator as extra context for every page of "
                "this project, so character names and recurring terms stay consistent. "
                "The base system prompt is never modified."
            )
        ).secondary()
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addWidget(MDivider())

        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(
            [self.tr("Term"), self.tr("Translation")]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        layout.addWidget(self.table, 1)

        # New-term row
        term_row = QtWidgets.QHBoxLayout()
        term_row.addWidget(MLabel(self.tr("Term:")))
        self.term_input = MLineEdit()
        term_row.addWidget(self.term_input, 1)
        term_row.addWidget(MLabel(self.tr("Translation:")))
        self.translation_input = MLineEdit()
        term_row.addWidget(self.translation_input, 1)
        layout.addLayout(term_row)

        buttons = QtWidgets.QHBoxLayout()
        self.add_button = MPushButton(self.tr("Add / Update")).small()
        self.remove_button = MPushButton(self.tr("Remove Selected")).small()
        self.load_button = MPushButton(self.tr("Load from File...")).small()
        self.save_button = MPushButton(self.tr("Save to File...")).small()
        self.clear_button = MPushButton(self.tr("Clear All")).small()

        self.add_button.clicked.connect(self._on_add_update)
        self.remove_button.clicked.connect(self._on_remove_selected)
        self.load_button.clicked.connect(self._on_load_file)
        self.save_button.clicked.connect(self._on_save_file)
        self.clear_button.clicked.connect(self._on_clear_all)

        for btn in (
            self.add_button,
            self.remove_button,
            self.load_button,
            self.save_button,
            self.clear_button,
        ):
            buttons.addWidget(btn)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        close_row = QtWidgets.QHBoxLayout()
        close_row.addStretch(1)
        close_button = MPushButton(self.tr("Close")).small()
        close_button.clicked.connect(self.accept)
        close_row.addWidget(close_button)
        layout.addLayout(close_row)

        self.term_input.returnPressed.connect(self._on_add_update)
        self.translation_input.returnPressed.connect(self._on_add_update)

        self._reload_table()

    # ------------------------------------------------------------------
    # Table <-> store
    # ------------------------------------------------------------------
    def _reload_table(self) -> None:
        self.table.setRowCount(0)
        for term, translation in self._store.get_terms().items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            term_item = QtWidgets.QTableWidgetItem(term)
            translation_item = QtWidgets.QTableWidgetItem(translation)
            term_item.setFlags(term_item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
            translation_item.setFlags(
                translation_item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable
            )
            self.table.setItem(row, COLUMN_TERM, term_item)
            self.table.setItem(row, COLUMN_TRANSLATION, translation_item)
        self.table.sortItems(COLUMN_TERM, QtCore.Qt.SortOrder.AscendingOrder)

    def _collect_from_table(self) -> dict[str, str]:
        terms: dict[str, str] = {}
        for row in range(self.table.rowCount()):
            term_item = self.table.item(row, COLUMN_TERM)
            translation_item = self.table.item(row, COLUMN_TRANSLATION)
            term = (term_item.text() if term_item else "").strip()
            translation = translation_item.text() if translation_item else ""
            if term:
                terms[term] = translation
        return terms

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_add_update(self) -> None:
        term = self.term_input.text().strip()
        if not term:
            self.term_input.setFocus()
            return
        translation = self.translation_input.text()
        self._store.set_term(term, translation)
        self.term_input.clear()
        self.translation_input.clear()
        self.term_input.setFocus()
        self._reload_table()

    def _on_remove_selected(self) -> None:
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            return
        for index in sorted(selected, key=lambda i: i.row(), reverse=True):
            item = self.table.item(index.row(), COLUMN_TERM)
            if item and item.text().strip():
                self._store.remove_term(item.text().strip())
        self._reload_table()

    def _on_clear_all(self) -> None:
        if self.table.rowCount() == 0:
            return
        ret = QtWidgets.QMessageBox.question(
            self,
            self.tr("Clear Glossary"),
            self.tr("Remove every term from this project's glossary?"),
        )
        if ret != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self._store.clear()
        self._reload_table()

    def _on_load_file(self) -> None:
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self.tr("Load Glossary"),
            "",
            self.tr("Glossary files (*.json);;All files (*)"),
        )
        if not file_name:
            return
        try:
            with open(file_name, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            QtWidgets.QMessageBox.warning(
                self,
                self.tr("Could Not Load Glossary"),
                self.tr("The selected file could not be read as a glossary:\n{error}").format(
                    error=str(exc)
                ),
            )
            return
        if not isinstance(data, dict):
            QtWidgets.QMessageBox.warning(
                self,
                self.tr("Invalid Glossary"),
                self.tr("A glossary file must contain term -> translation pairs."),
            )
            return
        self._store.set_terms(data)
        self._reload_table()

    def _on_save_file(self) -> None:
        # Keep the in-memory store authoritative even if the user only closes
        # the dialog afterwards; persisting into the project file is separate.
        self._store.set_terms(self._collect_from_table())
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self.tr("Save Glossary"),
            "glossary.json",
            self.tr("Glossary files (*.json);;All files (*)"),
        )
        if not file_name:
            return
        try:
            with open(file_name, "w", encoding="utf-8") as fh:
                json.dump(self._store.get_terms(), fh, ensure_ascii=False, indent=1)
        except OSError as exc:
            QtWidgets.QMessageBox.warning(
                self,
                self.tr("Could Not Save Glossary"),
                self.tr("The glossary could not be written:\n{error}").format(
                    error=str(exc)
                ),
            )

    def accept(self) -> None:
        # Last chance to pick up any in-table edits the user never confirmed.
        self._store.set_terms(self._collect_from_table())
        super().accept()
