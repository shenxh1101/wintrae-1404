import os, sys, time, shutil
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from src.config import Config
from src.state_manager import StateManager, compute_file_hash
from src.processor import EpisodeProcessor

cfg = Config()
# clean
state_dir = os.path.join(str(getattr(cfg, "output_dir", "./output")), ".state")
if os.path.isdir(state_dir):
    shutil.rmtree(state_dir, ignore_errors=True)
od = os.path.join(str(getattr(cfg, "output_dir", "./output")), "001")
if os.path.isdir(od):
    shutil.rmtree(od, ignore_errors=True)
os.makedirs(state_dir, exist_ok=True)

sm = StateManager(cfg)
proc = EpisodeProcessor(cfg, sm)
ep_dir = os.path.join(BASE, 'input', '001_AI产品的未来')
r0, review, errs = proc.preview_release(ep_dir)
print("preview OK, is_valid:", r0.is_valid)

# 正式发布（overwrite）
print("\n---正式发布 1")
r1, e1 = proc.confirm_and_release(r0, release_mode="release", reviewer="主编-B", conflict_policy="overwrite")
print("generated:", len(r1.generated_files), "conflicts:", len(r1.conflicts), "overwritten:", len(r1.files_overwritten), "preserved:", len(r1.files_preserved))

# 看 state 里 shownotes 的 hash
st = sm.get_or_create("001", ep_dir)
for k, v in st.file_hashes.items():
    if "shownotes" in k and "_v" not in k:
        print(f"  state hash: {k} = {v[:12]}")
shownotes_list = [f for f in r1.generated_files if "shownotes" in os.path.basename(f) and "_v" not in os.path.basename(f)]
sn = shownotes_list[0]
print(f"  disk shownotes hash = {compute_file_hash(sn)[:12]}")

# 再生成 2，看看还有没有冲突（应无）
print("\n--- 再生成 2 (preserve) 应无冲突")
r2, e2 = proc.confirm_and_release(r0, release_mode="release", reviewer="主编-B", conflict_policy="preserve")
print("conflicts:", len(r2.conflicts))
for c in r2.conflicts:
    print("  conflict:", c)

# 手改 shownotes
print("\n--- 手改 shownotes 再生成 3 (preserve)，应有冲突")
with open(sn, "r", encoding="utf-8") as f:
    content = f.read()
with open(sn, "w", encoding="utf-8") as f:
    f.write(content + "\n<!-- 手改 -->\n")
print(f"  disk after edit hash = {compute_file_hash(sn)[:12]}")
r3, e3 = proc.confirm_and_release(r0, release_mode="release", reviewer="主编-B", conflict_policy="preserve")
print("conflicts:", len(r3.conflicts))
for c in r3.conflicts:
    print("  conflict:", c)
st = sm.get_or_create("001", ep_dir)
for k, v in st.file_hashes.items():
    if "shownotes" in k and "_v" not in k:
        print(f"  state hash: {k} = {v[:12]}")

print("\n--- overwrite 再生成 4，应消除冲突")
r4, e4 = proc.confirm_and_release(r0, release_mode="release", reviewer="主编-B", conflict_policy="overwrite")
print("conflicts:", len(r4.conflicts))
st = sm.get_or_create("001", ep_dir)
for k, v in st.file_hashes.items():
    if "shownotes" in k and "_v" not in k:
        print(f"  state hash: {k} = {v[:12]}")
print(f"  disk after overwrite hash = {compute_file_hash(sn)[:12]}")

print("\n--- 再生成 5 (preserve)，应无冲突")
r5, e5 = proc.confirm_and_release(r0, release_mode="release", reviewer="主编-B", conflict_policy="preserve")
print("conflicts:", len(r5.conflicts))
for c in r5.conflicts:
    print("  conflict:", c)
