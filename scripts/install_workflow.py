from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
src=root/"workflow-template"/"update.yml"
dst=root/".github"/"workflows"/"update.yml"
dst.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(src,dst)
print("Created .github/workflows/update.yml; commit and push it to enable scheduled Actions.")
