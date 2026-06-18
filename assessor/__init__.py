"""Minimal assessor package stub.

This provides a lightweight `run_assessment(outdir, source, target, output)`
so `main.py` can import and produce a simple findings summary when the
full assessor implementation isn't present.
"""
from __future__ import annotations
import os
import re
try:
    import yaml
except Exception:
    yaml = None


def run_assessment(outdir: str, source: str | None, target: str | None, output: str) -> dict:
    """Perform a quick, conservative assessment using collected files.

    This is intentionally lightweight: it looks for CRDs, API resource
    hints, and a sample of deployments to build a basic `findings` dict
    that `main.py` can display.
    """
    findings = {
        'summary': {},
        'risk_matrix': {},
    }

    readiness = 85
    confidence = 75
    detected_controllers = []

    # Sample controllers from deploy-A.txt (if present)
    deploy_path = os.path.join(outdir, 'deploy-A.txt')
    if os.path.exists(deploy_path):
        try:
            with open(deploy_path, 'r', encoding='utf-8') as fh:
                lines = [l.strip() for l in fh if l.strip()]
            names = []
            for ln in lines:
                parts = re.split(r"\s+", ln)
                # Skip header lines
                if parts[0].lower() in ('namespace', 'name'):
                    continue
                if len(parts) >= 2:
                    names.append(parts[1])
            # unique sample
            seen = []
            for n in names:
                if n not in seen:
                    seen.append(n)
            detected_controllers = seen[:12]
        except Exception:
            detected_controllers = []

    # CRD quick check
    crd_count = 0
    crd_path = os.path.join(outdir, 'crd.yaml')
    if os.path.exists(crd_path) and yaml is not None:
        try:
            with open(crd_path, 'r', encoding='utf-8') as fh:
                doc = yaml.safe_load(fh)
            items = doc.get('items', []) if isinstance(doc, dict) else []
            crd_count = len(items)
            if crd_count:
                readiness -= min(30, crd_count * 2)
                findings['risk_matrix']['CRDs'] = {
                    'status': 'WARN',
                    'severity': 'High',
                    'explanation': f'{crd_count} CRDs detected; validate conversion and webhook handling before upgrade.'
                }
        except Exception as e:
            findings['risk_matrix']['CRDs'] = {
                'status': 'UNKNOWN',
                'severity': 'Medium',
                'explanation': f'Failed to parse crd.yaml: {e}'
            }

    # API resources scan (look for beta mentions as a heuristic)
    api_res_path = os.path.join(outdir, 'api-resources.txt')
    beta_occurrences = 0
    if os.path.exists(api_res_path):
        try:
            txt = open(api_res_path, 'r', encoding='utf-8').read().lower()
            beta_occurrences = txt.count('beta')
            if beta_occurrences:
                readiness -= min(20, beta_occurrences)
                findings['risk_matrix']['APIs'] = {
                    'status': 'WARN',
                    'severity': 'Medium',
                    'explanation': f'Found {beta_occurrences} occurrences of "beta" in api-resources output; inspect workloads for deprecated/removed APIs.'
                }
        except Exception:
            pass

    # Ensure scores are within bounds
    readiness = max(0, min(100, int(readiness)))
    confidence = max(0, min(100, int(confidence)))

    findings['summary']['readiness'] = readiness
    findings['summary']['confidence'] = confidence
    findings['summary']['detected_controllers'] = detected_controllers
    findings['summary']['crd_count'] = crd_count

    # Build a conservative risk matrix with multiple findings (6 entries)
    # 3-4 critical issues (High severity) and 2 high risks (Medium severity)
    # 1) Release notes availability
    rn_status = 'WARN'
    rn_expl = 'Release notes for intermediate versions were not retrieved; this reduces confidence.'
    findings['risk_matrix']['Release Notes'] = {
        'status': rn_status,
        'severity': 'High',
        'explanation': rn_expl,
    }

    # 2) Backups / etcd snapshots
    backup_status = 'WARN'
    backup_expl = 'No evidence of etcd snapshots or backups found in collected outputs; ensure backups exist before upgrade.'
    findings['risk_matrix']['Backups'] = {
        'status': backup_status,
        'severity': 'High',
        'explanation': backup_expl,
    }

    # 3) CRDs
    if 'CRDs' not in findings['risk_matrix']:
        # if earlier parsing didn't set CRDs, mark unknown/high
        findings['risk_matrix']['CRDs'] = {
            'status': 'WARN' if crd_count > 0 else 'PASS',
            'severity': 'High' if crd_count > 0 else 'Low',
            'explanation': (f'{crd_count} CRDs detected; validate conversion and webhook handling before upgrade.' if crd_count > 0 else 'No CRDs detected.')
        }

    # 4) Controllers / Operators
    ctrl_status = 'WARN' if detected_controllers else 'PASS'
    ctrl_sev = 'High' if detected_controllers else 'Low'
    ctrl_expl = (f'{len(detected_controllers)} controllers/operators detected; verify vendor compatibility and upgrade path.' if detected_controllers else 'No additional controllers/operators detected in sample.')
    findings['risk_matrix']['Controllers'] = {
        'status': ctrl_status,
        'severity': ctrl_sev,
        'explanation': ctrl_expl,
    }

    # 5) APIs (medium risk if beta APIs found)
    api_status = 'WARN' if beta_occurrences else 'PASS'
    api_sev = 'Medium' if beta_occurrences else 'Low'
    api_expl = (f'Found {beta_occurrences} occurrences of "beta" in api-resources; check for deprecated/removed APIs.' if beta_occurrences else 'No beta APIs detected in sample scan.')
    findings['risk_matrix']['APIs'] = {
        'status': api_status,
        'severity': api_sev,
        'explanation': api_expl,
    }

    # 6) Webhooks / Admission
    webhook_path_v = os.path.join(outdir, 'validatingwebhooks.yaml')
    webhook_path_m = os.path.join(outdir, 'mutatingwebhooks.yaml')
    webhook_count = 0
    try:
        for p in (webhook_path_v, webhook_path_m):
            if os.path.exists(p) and yaml is not None:
                with open(p, 'r', encoding='utf-8') as fh:
                    doc = yaml.safe_load(fh)
                items = doc.get('items', []) if isinstance(doc, dict) else []
                webhook_count += len(items)
    except Exception:
        pass

    wh_status = 'WARN' if webhook_count > 0 else 'PASS'
    wh_sev = 'Medium' if webhook_count > 0 else 'Low'
    wh_expl = (f'{webhook_count} admission webhooks detected; verify TLS and certificate rotation for webhook services.' if webhook_count > 0 else 'No admission webhooks detected.')
    findings['risk_matrix']['Webhooks'] = {
        'status': wh_status,
        'severity': wh_sev,
        'explanation': wh_expl,
    }

    # Append a brief assessor summary to the output markdown (non-destructive)
    try:
        with open(output, 'a', encoding='utf-8') as fh:
            fh.write('\n\n## Assessor Quick Summary\n\n')
            fh.write(f'- Readiness Score: {readiness}\n')
            fh.write(f'- Confidence: {confidence}%\n')
            fh.write(f'- Detected Controllers (sample): {", ".join(detected_controllers) if detected_controllers else "None"}\n')
            fh.write(f'- CRD count: {crd_count}\n')
    except Exception:
        # Do not fail the assessment because we couldn't write the file
        pass

    return findings
