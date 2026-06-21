import os, sys, shutil, time
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from src.config import Config
from src.state_manager import StateManager
from src.processor import EpisodeProcessor
from src.dashboard import EpisodeDashboard

cfg = Config()
state_dir = os.path.join(str(getattr(cfg, "output_dir", "./output")), ".state")
if os.path.isdir(state_dir):
    shutil.rmtree(state_dir, ignore_errors=True)
od = os.path.join(str(getattr(cfg, "output_dir", "./output")), "001")
if os.path.isdir(od):
    shutil.rmtree(od, ignore_errors=True)
os.makedirs(state_dir, exist_ok=True)

sm = StateManager(cfg)
proc = EpisodeProcessor(cfg, sm)
dsh = EpisodeDashboard(cfg, sm)
ep_dir = os.path.join(BASE, 'input', '001_AI产品的未来')
r0, review, errs = proc.preview_release(ep_dir)
print("preview OK is_valid=", r0.is_valid)
r1, e1 = proc.confirm_and_release(r0, release_mode="release", reviewer="主编-B", conflict_policy="overwrite")
print("after confirm_and_release, state:")
st = sm.get_or_create("001", ep_dir)
print("  last_scanned_at =", st.last_scanned_at)
print("  updated_at =", st.updated_at)
print("  _episodes keys =", list(sm._episodes.keys()))
print("  state.last_reviewed_at =", st.last_reviewed_at)
print("  state.reviewer =", st.reviewer)

print("\n--- scan 1")
rows1 = dsh.scan_with_options("all", save_state=True)
st1 = sm.get_or_create("001", ep_dir)
print("  scan 后 last_scanned_at =", st1.last_scanned_at)
print("  scan 后 updated_at =", st1.updated_at)
print("  scan 后 _episodes keys =", list(sm._episodes.keys()))
print("  _episodes[001].metadata.input_dir_mtime =", st1.metadata.get("input_dir_mtime", None))
print(f"  rows count={len(rows1)}, rows[0].episode_number={rows1[0].episode_number if rows1 else None}")

time.sleep(1.01)
print("\n--- scan 2")
rows2 = dsh.scan_with_options("all", save_state=True)
st2 = sm.get_or_create("001", ep_dir)
print("  last_scanned_at =", st2.last_scanned_at)
print("  updated_at =", st2.updated_at)

print("\n--- 看 episodes.json 保存情况")
ef = os.path.join(BASE, "output", ".state", "episodes.json")
with open(ef, "r", encoding="utf-8") as f:
    import json
    data = json.load(f)
for item in data:
    print(f"  ep={item.get('episode_number')}, last_scanned_at={item.get('last_scanned_at')}, updated_at={item.get('updated_at')}")
    print(f"     input_dir_mtime in metadata: {item.get('metadata', {}).get('input_dir_mtime')}")
