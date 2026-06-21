import os, sys, shutil, time
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from src.config import Config
from src.state_manager import StateManager

cfg = Config()
state_dir = os.path.join(str(getattr(cfg, "output_dir", "./output")), ".state")
if os.path.isdir(state_dir):
    shutil.rmtree(state_dir, ignore_errors=True)
os.makedirs(state_dir, exist_ok=True)

sm = StateManager(cfg)
st = sm.get_or_create("001", "some_dir")
print("before mark_scanned, last_scanned_at =", st.last_scanned_at, "id(state)=", id(st))
st2 = sm.mark_scanned("001", "some_dir", source_dir_mtime="2026-06-01T00:00:00")
print("after mark_scanned, st2.last_scanned_at =", st2.last_scanned_at if st2 else "no st2")
print("same st?", st is st2)
print("metadata:", st.metadata)
print("sm._dirty =", sm._dirty)
ok = sm.save()
print("save() returned", ok)
# read file
sf = os.path.join(BASE, "output", ".state", "episodes.json")
with open(sf, "r", encoding="utf-8") as f:
    import json
    data = json.load(f)
eps = data.get("episodes", {})
ep001 = eps.get("001", {})
print("json last_scanned_at =", ep001.get("last_scanned_at"))
print("json metadata =", ep001.get("metadata"))
print("st.last_scanned_at =", st.last_scanned_at)

print("\n--- dashboard.scan case:")
from src.processor import EpisodeProcessor
from src.dashboard import EpisodeDashboard
# reload fresh sm
sm2 = StateManager(cfg)
proc2 = EpisodeProcessor(cfg, sm2)
dsh2 = EpisodeDashboard(cfg, sm2)
ep_dir = os.path.join(BASE, 'input', '001_AI产品的未来')
r0, rv, errs = proc2.preview_release(ep_dir)
pkg, e1 = proc2.confirm_and_release(r0, release_mode="release", reviewer="X", conflict_policy="overwrite")
print("before scan, sm2['001'].last_scanned_at=", sm2.get("001").last_scanned_at)
print("before scan, state_manager._dirty=", sm2._dirty)
rows = dsh2.scan_with_options("all", save_state=True)
print("after scan, sm2['001'].last_scanned_at=", sm2.get("001").last_scanned_at)
print("after scan, state_manager._dirty=", sm2._dirty)
print("mark_scanned is called? Let's call manually")
st3 = sm2.mark_scanned("001", ep_dir, source_dir_mtime="2026-05-01")
print("manual mark -> last_scanned_at=", st3.last_scanned_at if st3 else None)
