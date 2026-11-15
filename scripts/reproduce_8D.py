from pathlib import Path
import hashlib
import pandas as pd
from scripts.plotting.final_figures import build_figures
from scripts.tables.final_tables import build_tables

SNAPSHOT = "snap_0cc46433731097c4"

def main():
    root = Path.cwd()
    build_figures(root)
    build_tables(root)

    artifacts = sorted(
        list((root / "figures/final").glob("*")) +
        list((root / "figures/supplementary").glob("*")) +
        list((root / "results/final_tables").glob("*"))
    )
    rows = []
    for p in artifacts:
        rows.append({
            "artifact": p.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "size_bytes": p.stat().st_size,
            "analysis_snapshot": SNAPSHOT,
        })
    manifest = root / "results/metadata/final_artifacts_8D_manifest.csv"
    pd.DataFrame(rows).to_csv(manifest, index=False)
    print(f"Generated {len(artifacts)} final 8D artifacts")
    print(f"Manifest: {manifest}")

if __name__ == "__main__":
    main()
