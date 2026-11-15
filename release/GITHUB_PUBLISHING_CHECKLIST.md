# GitHub publishing checklist — v1.0.0

1. From the repository root, run:

```bash
python -m pip install -r requirements.txt
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
pytest -q
python -m scripts.reproduce_8D
python scripts/release_check.py --structural
python scripts/freeze_release_manifest.py
python scripts/release_check.py --verify-frozen
python scripts/build_release_bundle.py
```

2. Commit the tree and push it:

```bash
git init
git add .
git commit -m "Release 1.0.0"
git branch -M main
git remote add origin <YOUR_GITHUB_REPOSITORY>
git push -u origin main
```

3. Tag the release:

```bash
git tag -a v1.0.0 -m "Kinetic Ising Standard vs n-fold v1.0.0"
git push origin v1.0.0
```

4. Create a GitHub Release from `v1.0.0`, paste `release/GITHUB_RELEASE_BODY.md`, and attach the ZIP and `.sha256` file from `dist/`.
