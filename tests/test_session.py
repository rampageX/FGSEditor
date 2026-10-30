import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication, QWidget
from fgseditor_qt import settings_manager as settings
from fgseditor_qt.fgs_parser import parse_fgs_events
from fgseditor_qt.fgs_save import build_dynamic_lines
from fgseditor_qt.window_state import remember_window

app = QApplication.instance() or QApplication([])

class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = settings.SETTINGS_FILE
        settings.SETTINGS_FILE = str(Path(self.temp.name)/'settings.json')
        settings.load_settings()
    def tearDown(self):
        settings.SETTINGS_FILE = self.old
        settings.load_settings()
        self.temp.cleanup()
    def test_directory_reload_and_fallback(self):
        folder = Path(self.temp.name)/"中文 & (Punk's)"
        folder.mkdir()
        settings.remember_directory('video', str(folder/'test.mkv'))
        settings.load_settings()
        self.assertEqual(settings.last_directory('video'), str(folder))
        self.assertNotEqual(settings.last_directory('table'), str(folder))
        folder.rmdir()
        self.assertNotEqual(settings.last_directory('video'), str(folder))
    def test_dynamic_roundtrip(self):
        text = Path('dynamic_fgs_test.txt').read_text()
        header, events = parse_fgs_events(text)
        events[0]['end_time'] = events[0]['start_time'] + 100
        before = [(e['start_time'],e['end_time'],e['extra_params']) for e in events]
        _, output = parse_fgs_events(''.join(build_dynamic_lines(header,events)))
        self.assertEqual(before, [(e['start_time'],e['end_time'],e['extra_params']) for e in output])
    def test_geometry_reload_and_offscreen(self):
        w = QWidget(); remember_window(w,'test'); w.resize(700,500); w.show(); app.processEvents()
        w.move(20,30); app.processEvents(); w.hide()
        saved = settings.get_setting('window_test'); self.assertTrue(saved)
        w2 = QWidget(); remember_window(w2,'test'); w2.show(); app.processEvents()
        self.assertEqual(w2.size(), w.size()); self.assertFalse(w2.isMinimized())
        w2.close(); w.close()
    def test_main_construct(self):
        from fgseditor_qt.main_ui import MainUI
        window = MainUI(); window.show(); app.processEvents()
        from unittest.mock import patch
        with patch.object(window.editor, "is_dirty", return_value=False):
            window.close()

if __name__ == '__main__':
    unittest.main()
