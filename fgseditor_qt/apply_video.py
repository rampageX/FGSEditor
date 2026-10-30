"""Apply an immutable snapshot without blocking Qt or changing the saved table."""
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog
from .settings_manager import last_directory, remember_directory
from .video_probe import probe_video, find_ffmpeg
from .grav1synth import get_grav1synth_path


class ApplyWorker(QThread):
    result = Signal(bool, str)

    def __init__(self, source, output, lines, parent=None):
        super().__init__(parent)
        self.source, self.output, self.lines = source, output, list(lines)
        self._cancel = threading.Event()

    def requestInterruption(self):
        self._cancel.set()
        super().requestInterruption()

    def isInterruptionRequested(self):
        return self._cancel.is_set() or super().isInterruptionRequested()

    def run_command(self, args):
        if self.isInterruptionRequested():
            raise InterruptedError("Cancelled. No output was published.")
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        with tempfile.TemporaryFile() as log:
            process = subprocess.Popen(args, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                                       creationflags=flags)
            while True:
                try:
                    process.wait(timeout=0.1)
                    break
                except subprocess.TimeoutExpired:
                    if self.isInterruptionRequested():
                        process.kill()
                        process.wait()
                        raise InterruptedError("Cancelled. No output was published.")
            if self.isInterruptionRequested():
                raise InterruptedError("Cancelled. No output was published.")
            if process.returncode:
                log.seek(0, 2)
                log.seek(max(0, log.tell()-12000))
                raise RuntimeError(log.read().decode("utf-8", "replace"))

    def run(self):
        try:
            info = probe_video(self.source)
            if info["codec"] != "av1":
                raise ValueError("Apply requires AV1 video.")
            # Same filesystem permits atomic, non-overwriting publication.
            with tempfile.TemporaryDirectory(prefix=".fgseditor-", dir=str(Path(self.output).parent)) as work:
                table = str(Path(work)/"current.txt")
                Path(table).write_text("".join(self.lines), encoding="utf-8")
                changed = str(Path(work)/"changed.mkv")
                staged = str(Path(work)/Path(self.output).name)
                self.run_command([get_grav1synth_path(), "apply", "-g", table, "-o", changed,
                                  "-y", "--replace", self.source])
                # grav1synth may drop attachments/data; remux those from the original.
                # No decoder or encoder is used. Unsupported streams fail rather than being dropped.
                metadata = []
                for key, value in info.get("tags", {}).items():
                    metadata.extend(["-metadata:s:v:0", f"{key}={value}"])
                disposition = info.get("disposition", {})
                if disposition:
                    metadata.extend(["-disposition:v:0", "+".join(k for k,v in disposition.items() if v) or "0"])
                self.run_command([find_ffmpeg(), "-nostdin", "-v", "error", "-n", "-i", changed,
                                  "-i", self.source, "-map", "0:v:0", "-map", "1", "-map", "-1:v:0",
                                  "-map_metadata", "1", "-map_chapters", "1", "-c", "copy", *metadata, staged])
                if self.isInterruptionRequested():
                    raise InterruptedError("Cancelled. No output was published.")
                if not os.path.getsize(staged):
                    raise RuntimeError("The output video is empty.")
                if sys.platform == "win32":
                    os.rename(staged, self.output)  # Windows rename never overwrites; works on SMB too.
                else:
                    os.link(staged, self.output)  # atomic, no-clobber publication on POSIX
            self.result.emit(True, "Video saved to:\n" + self.output)
        except Exception as exc:
            self.result.emit(False, str(exc))


def apply_current_table(parent, context, lines):
    if getattr(parent, "_apply_worker", None) is not None:
        return
    source = context._video_path
    if not source:
        source, _ = QFileDialog.getOpenFileName(parent, "Select target AV1 video", last_directory("video"),
                                               "AV1 Video (*.mkv *.mp4 *.ivf)")
        if not source:
            return
    try:
        if not get_grav1synth_path() or not find_ffmpeg():
            raise ValueError("Configure grav1synth and FFmpeg in Settings first.")
    except Exception as exc:
        QMessageBox.critical(parent, "Cannot Apply", str(exc))
        return
    default = Path(source).with_name(Path(source).stem + "_fgs_applied.mkv")
    i = 1
    while default.exists():
        default = Path(source).with_name(Path(source).stem + f"_fgs_applied_{i}.mkv")
        i += 1
    output, _ = QFileDialog.getSaveFileName(parent, "Save new video (existing files are protected)",
                                           str(default), "Matroska Video (*.mkv)")
    if not output:
        return
    if Path(output).suffix.lower() != ".mkv":
        output += ".mkv"
    if os.path.lexists(output) or os.path.normcase(os.path.realpath(source)) == os.path.normcase(os.path.realpath(output)):
        QMessageBox.warning(parent, "Output Protected", "Choose a new output filename. Existing files cannot be replaced.")
        return
    worker = ApplyWorker(os.path.abspath(source), os.path.abspath(output), lines, parent)
    parent._apply_worker = worker
    progress = QProgressDialog("Replacing AV1 grain metadata...", "Cancel", 0, 0, parent)
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(0)
    progress.setAutoClose(False)
    progress.canceled.connect(worker.requestInterruption)
    def result(ok, message):
        if ok:
            remember_directory("video", source)
        progress.close()
        (QMessageBox.information if ok else QMessageBox.warning)(parent, "Apply Complete" if ok else "Apply Stopped", message)
    def finished():
        parent._apply_worker = None
        worker.deleteLater()
        progress.deleteLater()
    worker.result.connect(result)
    worker.finished.connect(finished)
    progress.show()
    worker.start()
