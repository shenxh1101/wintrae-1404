import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from src.config import Config
from src.processor import EpisodeProcessor
from src.state_manager import StateManager
cfg = Config()
sm = StateManager(cfg)
proc = EpisodeProcessor(cfg, sm)
ep_dir = os.path.join(BASE, 'input', '001_AI产品的未来')
r, rv, errs = proc.preview_release(ep_dir)
print('is_valid:', getattr(r, 'is_valid', None))
v = getattr(r, 'validation', None)
print('missing:', getattr(v, 'missing_files', None))
print('naming:', getattr(v, 'naming_issues', None))
print('sw:', getattr(v, 'sensitive_words_found', None))
print('audio_info:', getattr(r, 'audio_info', None))
print('cover:', getattr(r, 'cover_info', None))
print('release_pkg:', getattr(r, 'release_package', None))
print('errors:', errs)
print('rendered review:')
print(rv[:500])
