"""Real Windows tool integration; fails on any lost audio/subtitle/chapter/attachment."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
from pathlib import Path
import subprocess
import tempfile
from PySide6.QtWidgets import QApplication
from fgseditor_qt.apply_video import ApplyWorker
from fgseditor_qt.settings_manager import set_setting
from fgseditor_qt.grav1synth import inspect_fgs
from fgseditor_qt.fgs_parser import parse_fgs_events
from fgseditor_qt.fgs_save import build_dynamic_lines

app = QApplication([])
set_setting('ffmpeg_path', os.environ['TEST_FFMPEG'])
set_setting('ffprobe_path', os.environ['TEST_FFPROBE'])
set_setting('grav1synth_path', os.environ['TEST_GRAV1SYNTH'])

def run(args):
    try:
        return subprocess.check_output(args, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.output.decode('utf-8','replace')) from exc

with tempfile.TemporaryDirectory() as root:
    folder = Path(root)/"中文 & (Punk's)"; folder.mkdir()
    (folder/'sub.srt').write_text('1\n00:00:00,000 --> 00:00:01,500\nTest subtitle\n', encoding='utf-8')
    (folder/'attachment.txt').write_text('retained attachment')
    (folder/'chapters.txt').write_text(';FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=2000\ntitle=Test\n')
    source = str(folder/'source.mkv'); output = str(folder/'output.mkv')
    run([os.environ['TEST_FFMPEG'],'-v','error','-f','lavfi','-i','testsrc2=s=64x64:r=12:d=2',
         '-f','lavfi','-i','sine=duration=2','-i',str(folder/'sub.srt'),'-i',str(folder/'chapters.txt'),
         '-map','0:v','-map','1:a','-map','2:s','-map_chapters','3','-c:v','libaom-av1','-cpu-used','8',
         '-c:a','flac','-c:s','srt','-attach',str(folder/'attachment.txt'),'-metadata:s:t','mimetype=text/plain',source])
    header, events = parse_fgs_events(Path('static_fgs_test.txt').read_text())
    events[0]['start_time']=0; events[0]['end_time']=5000000
    import copy
    second=copy.deepcopy(events[0]); second['start_time']=10000000; second['end_time']=15000000
    lines=build_dynamic_lines(header,[events[0],second])
    messages=[]
    worker=ApplyWorker(source,output,lines)
    worker.result.connect(lambda ok,msg: messages.append((ok,msg)))
    worker.run()
    assert messages and messages[0][0], messages
    probe=json.loads(run([os.environ['TEST_FFPROBE'],'-v','error','-show_streams','-show_chapters','-of','json',output]))
    assert sorted(s['codec_type'] for s in probe['streams']) == ['attachment','audio','subtitle','video'], probe
    assert probe['chapters'][0]['tags']['title']=='Test'
    for selector in ['a:0','s:0']:
        def hash_stream(path):
            return run([os.environ['TEST_FFMPEG'],'-v','error','-i',path,'-map',selector,'-c','copy','-f','hash','-hash','sha256','-'])
        assert hash_stream(source)==hash_stream(output), selector
    extracted=str(folder/'output.txt'); assert inspect_fgs(output,extracted)
    extracted_events=parse_fgs_events(Path(extracted).read_text())[1]
    def active(t):
        return any(e['start_time'] <= t < e['end_time'] for e in extracted_events)
    assert active(2500000) and active(12500000), extracted_events
    assert not active(7500000) and not active(17500000), 'A gap or finite tail was filled'

    def pixel_hashes(path):
        stripped = str(folder/(Path(path).stem + '_no_grain.mkv'))
        run([os.environ['TEST_GRAV1SYNTH'],'remove','-o',stripped,'-y',path])
        data=run([os.environ['TEST_FFMPEG'],'-v','error','-i',stripped,
                  '-map','0:v:0','-f','framemd5','-']).decode()
        return [line.rsplit(',',1)[1].strip() for line in data.splitlines() if line and not line.startswith('#')]
    assert pixel_hashes(source)==pixel_hashes(output), 'Video pixels changed when grain synthesis disabled'
    replacement=str(folder/'replaced.mkv')
    messages.clear()
    worker=ApplyWorker(output,replacement,lines)
    worker.result.connect(lambda ok,msg: messages.append((ok,msg)))
    worker.run()
    assert messages and messages[0][0], messages
    worker=ApplyWorker(source,str(folder/'cancelled.mkv'),lines)
    worker.start(); worker.requestInterruption(); worker.wait(); app.processEvents()
    assert not (folder/'cancelled.mkv').exists()
    assert not list(folder.glob('.fgseditor-*'))
    print('PASS: real AV1 metadata apply, special paths, audio/subtitle hashes, chapter, attachment, cancellation cleanup')
