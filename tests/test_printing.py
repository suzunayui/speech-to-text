import os
import unicodedata
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QFont, QFontDatabase, QPageSize
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QApplication

import app


@pytest.mark.parametrize("line_count", [1, 150])
def test_print_current_text_on_a4(tmp_path, monkeypatch, line_count):
    application = QApplication.instance() or QApplication([])
    # Qt's offscreen plugin does not discover system fonts on Windows.
    if os.name == "nt":
        font_id = QFontDatabase.addApplicationFont(
            str(Path(os.environ["WINDIR"]) / "Fonts" / "YuGothR.ttc")
        )
        assert font_id >= 0
        application.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0]))
    monkeypatch.setattr(app.MainWindow, "refresh_environment", lambda self: None)
    window = app.MainWindow()
    assert not window.print_button.isEnabled()
    window.output.setPlainText("   \n")
    assert not window.print_button.isEnabled()
    text = "\n".join(f"日本語の印刷確認 {i} <本文> & 編集済み" for i in range(line_count))
    window.output.setPlainText(text)
    assert window.print_button.isEnabled()
    output = tmp_path / "printed.pdf"

    def export_preview(preview):
        printer = preview.printer()
        assert printer.pageLayout().pageSize().id() == QPageSize.PageSizeId.A4
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(output))
        preview.paintRequested.emit(printer)
        return 0

    monkeypatch.setattr(app.QPrintPreviewDialog, "exec", export_preview)
    window.print_result()
    pdf = QPdfDocument()
    assert pdf.load(str(output)) == QPdfDocument.Error.None_
    application.processEvents()
    assert (pdf.pageCount() > 1) == (line_count > 1)
    for page in range(pdf.pageCount()):
        size = pdf.pagePointSize(page)
        assert size.width() == pytest.approx(595, abs=1)
        assert size.height() == pytest.approx(842, abs=1)
    content = "".join(pdf.getAllText(page).text() for page in range(pdf.pageCount()))
    # Embedded Japanese fonts can map shared glyphs to compatibility radicals.
    content = unicodedata.normalize("NFKC", content)
    assert "日本語" in content
    assert "<本文>" in content
    assert str(line_count - 1) in content
    assert "".join(content.split()) == "".join(text.split())
    assert window.output.toPlainText() == text
    window.output.clear()
    assert not window.print_button.isEnabled()
    pdf.close()
    window.close()
