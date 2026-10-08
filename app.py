from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QMarginsF, QThread, Qt, Signal
from PySide6.QtGui import (QDragEnterEvent, QDropEvent, QFont, QPageLayout,
    QPageSize, QTextDocument, QTextOption)
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QProgressBar, QPushButton, QPlainTextEdit,
    QVBoxLayout, QWidget)

from src.exporters import TranscriptSegment, as_srt, as_text, as_vtt
from src.media import extract_audio, ffmpeg_version
from src.transcriber import TranscriptionCancelled, best_device, create_model, transcribe

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg",
                        ".mp4", ".mov", ".mkv", ".webm", ".mpeg", ".mpga"}


class TranscriptionWorker(QThread):
    progress = Signal(int, str)
    completed = Signal(object, str, float, str)
    failed = Signal(str)

    def __init__(self, source: Path, model_size: str, language: str | None) -> None:
        super().__init__()
        self.source, self.model_size, self.language = source, model_size, language
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def _report(self, value: float) -> None:
        if self._cancelled:
            raise TranscriptionCancelled
        self.progress.emit(10 + round(value * 90), f"文字起こし中… {value:.0%}")

    def _run_on_device(self, audio: Path, device: str):
        label = "GPU (CUDA)" if device == "cuda" else "CPU"
        self.progress.emit(8, f"{label}用モデルを準備しています…")
        result = transcribe(create_model(self.model_size, device), audio,
                            self.language, self._report)
        return *result, label

    def run(self) -> None:
        try:
            self.progress.emit(1, "音声を抽出しています…")
            with tempfile.TemporaryDirectory(prefix="speech-to-text-") as temp_dir:
                audio = extract_audio(self.source, Path(temp_dir) / "audio.wav")
                device = best_device()
                try:
                    result = self._run_on_device(audio, device)
                except TranscriptionCancelled:
                    raise
                except Exception as gpu_error:
                    if device != "cuda":
                        raise
                    self.progress.emit(8, "GPUを利用できなかったためCPUへ切り替えています…")
                    try:
                        result = self._run_on_device(audio, "cpu")
                    except Exception as cpu_error:
                        raise RuntimeError(f"GPU処理に失敗しました: {gpu_error}\n\n"
                                           f"CPUへの切り替えにも失敗しました: {cpu_error}") from cpu_error
            if not self._cancelled:
                self.completed.emit(*result)
        except TranscriptionCancelled:
            self.failed.emit("処理をキャンセルしました。")
        except Exception as exc:
            self.failed.emit(str(exc))


class DropArea(QLabel):
    file_dropped = Signal(str)

    def __init__(self) -> None:
        super().__init__("ここへ動画・音声ファイルをドロップ\nまたは下のボタンから選択")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumHeight(130)
        self.setStyleSheet("QLabel { border: 2px dashed #888; border-radius: 10px; "
                           "padding: 20px; color: #555; background: #fafafa; }")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        self.file_dropped.emit(event.mimeData().urls()[0].toLocalFile())
        event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.source: Path | None = None
        self.worker: TranscriptionWorker | None = None
        self.segments: list[TranscriptSegment] = []
        self.setWindowTitle("動画・音声文字起こし")
        self.resize(820, 680)
        root, layout = QWidget(), QVBoxLayout()
        root.setLayout(layout)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("動画・音声の文字起こし")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        layout.addWidget(QLabel("ファイルは外部へ送信せず、このコンピューター上で処理します。"))

        settings = QHBoxLayout()
        settings.addWidget(QLabel("モデル:"))
        self.model_combo = QComboBox(); self.model_combo.addItems(["small", "base", "medium", "large-v3", "turbo"])
        settings.addWidget(self.model_combo); settings.addSpacing(20); settings.addWidget(QLabel("言語:"))
        self.language_combo = QComboBox(); self.language_combo.addItems(["自動判定", "日本語", "英語"])
        settings.addWidget(self.language_combo); settings.addStretch()
        self.device_label = QLabel(); settings.addWidget(self.device_label); layout.addLayout(settings)

        self.drop_area = DropArea(); self.drop_area.file_dropped.connect(self.select_file); layout.addWidget(self.drop_area)
        formats_label = QLabel(
            "対応形式: MP3 / WAV / M4A / AAC / FLAC / OGG / "
            "MP4 / MOV / MKV / WebM / MPEG / MPGA"
        )
        formats_label.setWordWrap(True)
        formats_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(formats_label)
        file_row = QHBoxLayout(); self.file_label = QLabel("ファイルが選択されていません")
        choose = QPushButton("ファイルを選択"); choose.clicked.connect(self.open_file_dialog)
        choose.setStyleSheet(
            "QPushButton { background-color: #198754; color: white; "
            "font-weight: bold; border: none; border-radius: 6px; "
            "padding: 9px 18px; }"
            "QPushButton:hover { background-color: #157347; }"
            "QPushButton:pressed { background-color: #146c43; }"
        )
        file_row.addWidget(self.file_label, 1); file_row.addWidget(choose); layout.addLayout(file_row)
        action_row = QHBoxLayout(); self.start_button = QPushButton("文字起こしを開始")
        self.start_button.setEnabled(False); self.start_button.clicked.connect(self.start_transcription)
        self.cancel_button = QPushButton("キャンセル"); self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_transcription)
        action_row.addWidget(self.start_button); action_row.addWidget(self.cancel_button); layout.addLayout(action_row)
        self.progress = QProgressBar(); layout.addWidget(self.progress)
        self.status_label = QLabel("準備完了"); layout.addWidget(self.status_label)
        self.output = QPlainTextEdit(); self.output.setPlaceholderText("文字起こし結果がここに表示されます")
        layout.addWidget(self.output, 1)
        save_row = QHBoxLayout()
        self.save_buttons = []
        for kind in ("txt", "srt", "vtt"):
            button = QPushButton(f"{kind.upper()}を保存"); button.setEnabled(False)
            button.clicked.connect(lambda _checked=False, value=kind: self.save_result(value))
            self.save_buttons.append(button); save_row.addWidget(button)
        self.print_button = QPushButton("A4で印刷")
        self.print_button.setEnabled(False)
        self.print_button.clicked.connect(self.print_result)
        self.output.textChanged.connect(self.update_print_button)
        save_row.addWidget(self.print_button)
        layout.addLayout(save_row); self.setCentralWidget(root); self.refresh_environment()

    def refresh_environment(self) -> None:
        device = "GPU (CUDA) 優先" if best_device() == "cuda" else "CPU"
        try:
            version = ffmpeg_version().split(" Copyright", 1)[0]
            self.device_label.setText(f"処理デバイス: {device} | {version}")
        except Exception:
            self.device_label.setText(f"処理デバイス: {device}")

    def open_file_dialog(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "動画・音声ファイルを選択", "",
            "メディア (*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.mp4 *.mov *.mkv *.webm *.mpeg *.mpga);;すべて (*)")
        if filename: self.select_file(filename)

    def select_file(self, filename: str) -> None:
        path = Path(filename)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            QMessageBox.warning(self, "未対応の形式", "対応している動画・音声ファイルを選択してください。")
            return
        self.source = path; self.file_label.setText(str(path)); self.start_button.setEnabled(True)

    def start_transcription(self) -> None:
        if self.source is None: return
        language = {"自動判定": None, "日本語": "ja", "英語": "en"}[self.language_combo.currentText()]
        self.set_busy(True); self.output.clear(); self.progress.setValue(0)
        self.worker = TranscriptionWorker(self.source, self.model_combo.currentText(), language)
        self.worker.progress.connect(self.on_progress); self.worker.completed.connect(self.on_completed)
        self.worker.failed.connect(self.on_failed); self.worker.start()

    def set_busy(self, busy: bool) -> None:
        self.start_button.setEnabled(not busy and self.source is not None)
        self.cancel_button.setEnabled(busy); self.model_combo.setEnabled(not busy); self.language_combo.setEnabled(not busy)

    def cancel_transcription(self) -> None:
        if self.worker: self.status_label.setText("キャンセルしています…"); self.cancel_button.setEnabled(False); self.worker.cancel()

    def on_progress(self, value: int, message: str) -> None:
        self.progress.setValue(value); self.status_label.setText(message)

    def on_completed(self, segments, language: str, probability: float, device: str) -> None:
        self.segments = segments; self.output.setPlainText(as_text(segments).rstrip()); self.progress.setValue(100)
        self.status_label.setText(f"完了 — 言語: {language}（確度 {probability:.0%}）/ 使用: {device}")
        self.set_busy(False)
        for button in self.save_buttons: button.setEnabled(True)

    def on_failed(self, message: str) -> None:
        self.set_busy(False); self.status_label.setText(message)
        if message != "処理をキャンセルしました。": QMessageBox.critical(self, "処理に失敗しました", message)

    def save_result(self, kind: str) -> None:
        if not self.segments: return
        filename, _ = QFileDialog.getSaveFileName(self, "保存先", f"{self.source.stem}.{kind}", f"{kind.upper()} (*.{kind})")
        if filename:
            content = {"txt": as_text, "srt": as_srt, "vtt": as_vtt}[kind](self.segments)
            Path(filename).write_text(content, encoding="utf-8-sig" if kind == "txt" else "utf-8")

    def update_print_button(self) -> None:
        self.print_button.setEnabled(bool(self.output.toPlainText().strip()))

    def print_result(self) -> None:
        text = self.output.toPlainText()
        if not text.strip():
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageLayout(QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait,
            QMarginsF(20, 20, 20, 20), QPageLayout.Unit.Millimeter,
        ))
        printer.setDocName("文字起こし")
        # Keep a separate document so printing does not alter the editor layout.
        document = QTextDocument()
        font = QFont(self.output.font())
        font.setPointSizeF(12)
        document.setDefaultFont(font)
        option = document.defaultTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        document.setDefaultTextOption(option)
        document.setDocumentMargin(4)
        document.setPlainText(text)
        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("A4印刷プレビュー")
        preview.resize(900, 750)
        def render(target: QPrinter) -> None:
            document.documentLayout().setPaintDevice(target)
            document.setPageSize(target.pageRect(QPrinter.Unit.DevicePixel).size())
            document.print_(target)

        preview.paintRequested.connect(render)
        preview.exec()

    def closeEvent(self, event) -> None:
        if self.worker and self.worker.isRunning():
            if QMessageBox.question(self, "終了", "処理中です。終了しますか？") != QMessageBox.StandardButton.Yes:
                event.ignore(); return
            self.worker.cancel(); self.worker.wait(3000)
        event.accept()


def main() -> int:
    application = QApplication(sys.argv); application.setApplicationName("動画・音声文字起こし")
    window = MainWindow(); window.show(); return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
