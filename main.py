import os
import subprocess
import argparse
import shutil
from datetime import datetime
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional; continue if not installed
    pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

DEFAULT_DIR = "k8s-assessment-outputs"

COMMANDS = [
    ("kubectl version --output=yaml", "kubectl-version.yaml"),
    ("kubectl cluster-info", "cluster-info.txt"),
    ("kubectl get nodes -o wide", "nodes-wide.txt"),
    ("kubectl get nodes -o yaml", "nodes.yaml"),
    ("kubectl get namespaces", "namespaces.txt"),
    ("kubectl api-resources", "api-resources.txt"),
    ("kubectl get apiservices -o yaml", "apiservices.yaml"),
    ("kubectl get all -A", "all-A.txt"),
    ("kubectl get deploy -A", "deploy-A.txt"),
    ("kubectl get sts -A", "sts-A.txt"),
    ("kubectl get ds -A", "ds-A.txt"),
    ("kubectl get jobs -A", "jobs-A.txt"),
    ("kubectl get cronjobs -A", "cronjobs-A.txt"),
    ("kubectl get crd -o wide", "crd-wide.txt"),
    ("kubectl get crd -o yaml", "crd.yaml"),
    ("kubectl get validatingwebhookconfigurations -o yaml", "validatingwebhooks.yaml"),
    ("kubectl get mutatingwebhookconfigurations -o yaml", "mutatingwebhooks.yaml"),
    ("kubectl get csidrivers -A", "csidrivers.txt"),
    ("kubectl get storageclass -o yaml", "storageclass.yaml"),
    ("kubectl get pv,pvc -A", "pv-pvc-A.txt"),
    ("kubectl get pods -A -o wide", "pods-A-wide.txt"),
    ("kubectl top nodes", "top-nodes.txt"),
    ("kubectl top pods -A", "top-pods-A.txt"),
    ("kubectl get events -A --sort-by=.metadata.creationTimestamp", "events-A.txt"),
]


def run_cmd(cmd, dest_path):
    """Run a shell command and write stdout/stderr to dest_path."""
    try:
        completed = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        out = completed.stdout or ""
        err = completed.stderr or ""
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(out)
            if err:
                f.write("\n\n# STDERR:\n")
                f.write(err)
    except Exception as e:
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(f"Failed to run `{cmd}`\nError: {e}\n")


def gather_outputs(outdir: str):
    os.makedirs(outdir, exist_ok=True)
    for cmd, filename in COMMANDS:
        path = os.path.join(outdir, filename)
        print(f"Running: {cmd} -> {filename}")
        run_cmd(cmd, path)


def make_archive(outdir: str):
    base_name = outdir
    archive = shutil.make_archive(base_name, 'zip', root_dir=outdir)
    return archive


def write_report(outdir: str, archive_path: str | None, source: str | None, target: str | None, output: str):
    files = []
    for root, _, filenames in os.walk(outdir):
        for fn in filenames:
            rel = os.path.relpath(os.path.join(root, fn), outdir)
            files.append(rel)

    with open(output, "w", encoding="utf-8") as f:
        f.write("# Kubernetes Upgrade Collection Report\n\n")
        f.write(f"- Source Version: {source or 'N/A'}\n")
        f.write(f"- Target Version: {target or 'N/A'}\n")
        f.write(f"- Collected directory: {outdir}\n")
        f.write(f"- Archive: {archive_path or 'not created'}\n\n")
        f.write("## Collected files\n\n")
        for fn in sorted(files):
            f.write(f"- {fn}\n")


def main():
    parser = argparse.ArgumentParser(description="Kubernetes upgrade assessment helper")
    parser.add_argument("--outdir", default=None, help="Output directory (default: timestamped)")
    parser.add_argument("--no-archive", action="store_true", help="Do not create zip archive")
    parser.add_argument("-s", "--source", help="SOURCE_VERSION (e.g. 1.25)")
    parser.add_argument("-t", "--target", help="TARGET_VERSION (e.g. 1.26)")
    parser.add_argument("-o", "--output", default="report.md", help="Report output file (markdown)")
    args = parser.parse_args()

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    outdir = args.outdir or f"{DEFAULT_DIR}-{timestamp}"

    # Banner similar to screenshot
    model_name = os.environ.get('MODEL', 'assistant')
    cluster_status = 'live'
    banner = Table.grid(expand=False)
    banner.add_column(justify='right')
    banner.add_column(justify='left')
    banner.add_row('Source :', args.source or 'N/A')
    banner.add_row('Target :', args.target or 'N/A')
    banner.add_row('Model  :', model_name)
    banner.add_row('Cluster:', cluster_status)

    console.print(Panel(banner, title='Kubernetes Upgrade AI', subtitle='Upgrade Assessment', box=box.ROUNDED, style='cyan'))

    console.rule('[green]Collecting cluster data')
    console.log(f'Gathering kubectl outputs into: {outdir}')
    gather_outputs(outdir)
    console.log('Cluster data collected.')

    archive = None
    if not args.no_archive:
        archive = make_archive(outdir)
        console.log(f'Created archive: {archive}')
    else:
        console.log('Archive creation skipped.')

    # generate markdown report summarizing collection and requested versions
    try:
        write_report(outdir, archive, args.source, args.target, args.output)
        console.log(f'Wrote collection summary: {args.output}')
    except Exception as e:
        console.log(f'Failed to write collection summary: {e}')

    console.rule('[blue]Running assessment')
    # run the fuller assessment pipeline (assessor package)
    try:
        from assessor import run_assessment
        findings = run_assessment(outdir, args.source, args.target, args.output)
        console.log(f'Assessment complete. Report: {args.output}')

        # Present concise professional summary in terminal
        summary_tbl = Table(title='Assessment Summary', box=box.MINIMAL)
        summary_tbl.add_column('Metric', no_wrap=True)
        summary_tbl.add_column('Value')
        readiness = findings.get('summary', {}).get('readiness', 'N/A')
        confidence = findings.get('summary', {}).get('confidence', 'N/A')
        detected = findings.get('summary', {}).get('detected_controllers', [])
        summary_tbl.add_row('Readiness Score', str(readiness))
        summary_tbl.add_row('Confidence', f"{confidence}%")
        summary_tbl.add_row('Detected Controllers', ', '.join(detected) if detected else 'None')
        console.print(summary_tbl)

        # Risk highlights
        risk_tbl = Table(title='Top Risk Areas', box=box.MINIMAL)
        risk_tbl.add_column('Area')
        risk_tbl.add_column('Status')
        risk_tbl.add_column('Severity')
        risk_tbl.add_column('Explanation')
        for area, v in findings.get('risk_matrix', {}).items():
            if v.get('status') not in (None, 'PASS', 'GOOD'):
                risk_tbl.add_row(area, v.get('status') or 'UNKNOWN', v.get('severity') or 'Medium', v.get('explanation') or '')
        console.print(risk_tbl)

        # Human-style analyst commentary (concise)
        readiness_val = None
        try:
            readiness_val = int(readiness)
        except Exception:
            pass

        if readiness_val is None:
            commentary = (
                "Preliminary assessment complete. Review the full report for details. "
                "This summary is based on an automated scan and should be reviewed by an engineer."
            )
        elif readiness_val >= 90:
            commentary = (
                "Preliminary assessment: Ready to proceed with upgrade after standard pre-upgrade checks. "
                "Confirm operator compatibility and backups before starting."
            )
        elif readiness_val >= 75:
            commentary = (
                "Preliminary assessment: Ready with remediation. Address the items listed in the report's 'Required Pre-upgrade Actions' section, "
                "then re-run the assessment and validate in staging."
            )
        else:
            commentary = (
                "Preliminary assessment: Significant risk detected. Do not upgrade until the identified CRD and API issues are resolved. "
                "Use the report to prioritize fixes and validate in a staging environment."
            )

        console.print(Panel(commentary, title='Analyst Commentary', style='magenta'))

    except Exception as e:
        console.log(f'Assessor run failed or assessor package not available: {e}')


if __name__ == "__main__":
    main()
