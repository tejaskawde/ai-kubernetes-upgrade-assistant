Kubernetes Upgrade Assessment

This project collects Kubernetes cluster state via `kubectl` and performs a conservative, evidence-based upgrade readiness assessment between a SOURCE and TARGET Kubernetes version.

Quick start (WSL)

1. Create and activate venv (see `scripts/setup_venv_wsl.sh`)

2. Install requirements:

```bash
python -m pip install -r requirements.txt
```

3. Run the collector and assessment (provide source/target):

```bash
python main.py -s 1.34 -t 1.35 -o report.md
```

4. Upload the generated `k8s-assessment-outputs-*.zip` or open `report.md` for the assessment summary.

Notes

- The release notes fetch is best-effort and requires internet access.
- The tool is conservative: if it cannot verify compatibility it classifies the area as a risk and reduces confidence.
- This is an automated assistant. Manual review of `crd.yaml`, operator versions, and vendor compatibility matrices is required for final sign-off.
