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
<<<<<<< HEAD
try:
    import yaml
except Exception:
    yaml = None
=======
>>>>>>> b4f0b28606631623f461d69b0cb8b00b578c85d3

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
<<<<<<< HEAD
        # Run commands silently; outputs are written to files in outdir
        run_cmd(cmd, path)


def summarize_cluster(outdir: str):
    """Return a dict of concise cluster info parsed from collected outputs."""
    info = {
        'kubernetes_version': None,
        'api_server_version': None,
        'node_versions': set(),
        'os_images': set(),
        'container_runtimes': set(),
        'managed_hint': 'Unknown',
        'ha_topology': 'Unknown',
        'node_count': 0,
        'control_plane': 'Unknown',
    }

    # kubectl-version.yaml
    kvpath = os.path.join(outdir, 'kubectl-version.yaml')
    if os.path.exists(kvpath) and yaml is not None:
        try:
            with open(kvpath, 'r', encoding='utf-8') as fh:
                doc = yaml.safe_load(fh)
            server = doc.get('serverVersion') if isinstance(doc, dict) else None
            if server:
                ver = server.get('gitVersion') or server.get('git_version')
                if ver:
                    info['kubernetes_version'] = ver
                    info['api_server_version'] = ver
        except Exception:
            pass

    # nodes.yaml
    nodes_path = os.path.join(outdir, 'nodes.yaml')
    control_plane_nodes = 0
    if os.path.exists(nodes_path) and yaml is not None:
        try:
            with open(nodes_path, 'r', encoding='utf-8') as fh:
                doc = yaml.safe_load(fh)
            items = doc.get('items', []) if isinstance(doc, dict) else []
            node_names = []
            for n in items:
                info_n = n.get('status', {}).get('nodeInfo', {})
                if info_n:
                    kv = info_n.get('kubeletVersion')
                    if kv:
                        info['node_versions'].add(kv)
                    osim = info_n.get('osImage')
                    if osim:
                        info['os_images'].add(osim)
                    cr = info_n.get('containerRuntimeVersion')
                    if cr:
                        info['container_runtimes'].add(cr)
                labels = n.get('metadata', {}).get('labels', {}) or {}
                # capture node names to help detect Kind clusters
                name = n.get('metadata', {}).get('name', '')
                if name:
                    node_names.append(name)
                # heuristics for control-plane/master role
                if 'node-role.kubernetes.io/control-plane' in labels or 'node-role.kubernetes.io/master' in labels:
                    control_plane_nodes += 1
            # node count
            info['node_count'] = len(items)
            # detect kind by node name heuristics
            try:
                for nn in node_names:
                    if nn.startswith('kind-') or 'kind' in nn:
                        info['managed_hint'] = 'Kind'
                        break
            except Exception:
                pass
            # control plane simple label
            if control_plane_nodes == 0:
                info['control_plane'] = 'Unknown'
            elif control_plane_nodes == 1:
                info['control_plane'] = 'Single'
            else:
                info['control_plane'] = 'HA'
            # HA topology heuristic
            if control_plane_nodes == 0:
                info['ha_topology'] = 'Unknown (no control-plane node labels detected)'
            elif control_plane_nodes == 1:
                info['ha_topology'] = 'Single control-plane'
            else:
                info['ha_topology'] = f'{control_plane_nodes} control-plane nodes (HA)'
        except Exception:
            pass

    # cluster-info.txt heuristic for managed hints
    cluster_info_path = os.path.join(outdir, 'cluster-info.txt')
    if os.path.exists(cluster_info_path):
        try:
            txt = open(cluster_info_path, 'r', encoding='utf-8').read().lower()
            if 'kind control plane' in txt or 'kind cluster' in txt or 'kind' in txt:
                info['managed_hint'] = 'Kind'
            elif 'eks' in txt or 'amazon' in txt:
                info['managed_hint'] = 'EKS / AWS managed'
            elif 'gke' in txt or 'google' in txt:
                info['managed_hint'] = 'GKE / Google managed'
            elif 'aks' in txt or 'microsoft' in txt:
                info['managed_hint'] = 'AKS / Azure managed'
            else:
                # leave Unknown
                pass
        except Exception:
            pass

    # Normalize sets to sorted lists or comma strings
    info['node_versions'] = ', '.join(sorted(info['node_versions'])) if info['node_versions'] else 'N/A'
    info['os_images'] = ', '.join(sorted(info['os_images'])) if info['os_images'] else 'N/A'
    info['container_runtimes'] = ', '.join(sorted(info['container_runtimes'])) if info['container_runtimes'] else 'N/A'
    return info


def recommended_artifacts():
    """Return a list of recommended artifacts to collect before upgrading.

    Each item is a tuple: (label, example command or path, reason).
    """
    items = [
        ("kubeconfig", "~/.kube/config", "Access to the cluster for verification and re-running commands."),
        ("etcd snapshot", "ETCDCTL snapshot save /backups/etcd-snap.db", "A current etcd snapshot for disaster recovery."),
        ("All CRD YAMLs", "kubectl get crd -o yaml > crd.yaml", "CRD schemas and storedVersions to validate conversion and migration."),
        ("Operator/Controller versions", "kubectl get deploy -A -o wide > deploy-A.txt", "Operator images and versions to check vendor compatibility."),
        ("API usage scan", "kubectl get apiservices && kubectl api-resources > api-resources.txt", "Detect deprecated or removed APIs in use."),
        ("Admission webhook configs", "kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations -o yaml", "TLS and service connectivity for webhooks that may block upgrades."),
        ("Storage inventory", "kubectl get storageclass,pv,pvc -A -o yaml", "Check CSI drivers, reclaim policies, and in-use storage for compatibility."),
        ("Node inventory", "kubectl get nodes -o yaml", "Kubelet, kernel, container runtime and OS details for node remediation."),
        ("Pod Disruption Budgets and Readiness", "kubectl get pdb -A && kubectl get pods -A -o wide", "Ensure apps tolerate disruption and restart correctly."),
        ("Monitoring and alerts", "Prometheus rules, alertmanager configs, Grafana dashboards", "Capture current alerting thresholds to detect regression during upgrade."),
        ("Backup plan and restore runbook", "Operational runbook for restoring cluster/services", "Clear steps for recovery if upgrade fails."),
        ("Network/CNI details", "CNI plugin version and configuration (e.g., calico/2023.yaml)", "CNI compatibility is critical across Kubernetes versions."),
        ("Ingress / LB configs", "Ingress controller versions and Service/LoadBalancer configs", "External connectivity and controller compatibility."),
        ("RBAC & Policies", "kubectl get clusterrole,clusterrolebinding -A -o yaml", "Policy changes may alter permissions post-upgrade."),
    ]
    return items


=======
        print(f"Running: {cmd} -> {filename}")
        run_cmd(cmd, path)


>>>>>>> b4f0b28606631623f461d69b0cb8b00b578c85d3
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
<<<<<<< HEAD
        # (Node OS details intentionally omitted from report)
=======
>>>>>>> b4f0b28606631623f461d69b0cb8b00b578c85d3


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
<<<<<<< HEAD
    banner.add_row('Analysis Engine:', 'OpenAI GPT-5')
=======
    banner.add_row('Model  :', model_name)
>>>>>>> b4f0b28606631623f461d69b0cb8b00b578c85d3
    banner.add_row('Cluster:', cluster_status)

    console.print(Panel(banner, title='Kubernetes Upgrade AI', subtitle='Upgrade Assessment', box=box.ROUNDED, style='cyan'))

    console.rule('[green]Collecting cluster data')
    console.log(f'Gathering kubectl outputs into: {outdir}')
<<<<<<< HEAD
    with console.status('Collecting kubectl outputs (running quietly)...'):
        gather_outputs(outdir)
    console.log('Cluster data collected.')

    # Print a concise cluster summary (hide kubectl command noise)
    try:
        summary = summarize_cluster(outdir)
        info_tbl = Table.grid(expand=False)
        info_tbl.add_column(justify='left')
        info_tbl.add_column(justify='left')
        info_tbl.add_row('Cluster Type:', summary.get('managed_hint') or 'Kind')
        info_tbl.add_row('Kubernetes Version:', summary.get('kubernetes_version') or 'N/A')
        info_tbl.add_row('Target Version:', args.target or 'N/A')
        info_tbl.add_row('Node Count:', str(summary.get('node_count') or 'N/A'))
        info_tbl.add_row('Control Plane:', summary.get('control_plane') or 'Unknown')
        info_tbl.add_row('Readiness Score:', 'N/A')
        console.print(Panel(info_tbl, title='Cluster Summary', style='green'))
    except Exception as e:
        console.log(f'Failed to build concise cluster summary: {e}')

=======
    gather_outputs(outdir)
    console.log('Cluster data collected.')

>>>>>>> b4f0b28606631623f461d69b0cb8b00b578c85d3
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

<<<<<<< HEAD
    # (Pre-upgrade Checklist panel removed per user request)

    # Node OS table removed per user request; details remain in collected files

    console.rule('[blue]Running assessment')
    # Show an IMPORTANT summary before running the assessor
    try:
        imp_tbl = Table.grid(expand=False)
        imp_tbl.add_column(justify='left')
        imp_tbl.add_column(justify='left')
        cur = summarize_cluster(outdir)
        imp_tbl.add_row('IMPORTANT - Cluster Type:', cur.get('managed_hint') or 'Unknown')
        imp_tbl.add_row('IMPORTANT - Kubernetes Version:', cur.get('kubernetes_version') or 'N/A')
        imp_tbl.add_row('IMPORTANT - Node Count:', str(cur.get('node_count') or 'N/A'))
        imp_tbl.add_row('Output Directory:', outdir)
        console.print(Panel(imp_tbl, title='IMPORTANT', style='bold red'))
    except Exception:
        pass

=======
    console.rule('[blue]Running assessment')
>>>>>>> b4f0b28606631623f461d69b0cb8b00b578c85d3
    # run the fuller assessment pipeline (assessor package)
    try:
        from assessor import run_assessment
        findings = run_assessment(outdir, args.source, args.target, args.output)
        console.log(f'Assessment complete. Report: {args.output}')

<<<<<<< HEAD
        # Present professional terminal summary matching requested format
        def print_professional_summary(findings):
            s = findings.get('summary', {})
            readiness = int(s.get('readiness') or 0)
            confidence = int(s.get('confidence') or 0)
            detected = s.get('detected_controllers', []) or []

            # Decision mapping
            if readiness >= 90:
                decision = 'PROCEED'
            elif readiness >= 75:
                decision = 'CONDITIONAL'
            else:
                decision = 'DO NOT PROCEED'

            # Cluster summary (reuse summarize_cluster)
            cluster_info = summarize_cluster(outdir)

            # Build header block
            header = Table.grid(expand=False)
            header.add_column()
            header.add_column()
            header.add_row('UPGRADE DECISION:', decision)
            header.add_row('SOURCE VERSION:', args.source or 'N/A')
            header.add_row('TARGET VERSION:', args.target or 'N/A')
            header.add_row('READINESS SCORE:', f"{readiness}/100")
            header.add_row('CONFIDENCE:', f"{confidence}%")
            header.add_row('Analysis Engine:', 'OpenAI GPT-5')
            console.print(Panel(header, title='Executive Summary', style='bright_green'))

            # Critical issues / high risks / warnings
            critical = []
            high_risks = []
            warnings = []
            for area, v in findings.get('risk_matrix', {}).items():
                status = (v.get('status') or '').upper()
                sev = (v.get('severity') or '').upper()
                expl = v.get('explanation') or ''
                if sev == 'HIGH' and status not in ('PASS', 'GOOD'):
                    critical.append(f"- {area}: {expl}")
                elif status in ('WARN',) or sev == 'MEDIUM':
                    high_risks.append(f"- {area}: {expl}")
                else:
                    # treat other non-pass as warnings
                    if status and status not in ('PASS', 'GOOD'):
                        warnings.append(f"- {area}: {expl}")

            console.print(Panel('\n'.join(['CRITICAL ISSUES:'] + (critical or ['- None identified.'])), title='Critical Issues', style='red'))
            console.print(Panel('\n'.join(['HIGH RISKS:'] + (high_risks or ['- None identified.'])), title='High Risks', style='yellow'))
            if warnings:
                console.print(Panel('\n'.join(['WARNINGS:'] + warnings), title='Warnings', style='orange_red'))

            # Required actions (basic autogenerated recommendations)
            reqs = [
                'Verify release notes for versions ' + (f"{args.source} to {args.target}" if args.source and args.target else 'requested range'),
                'Ensure backup of critical data and etcd snapshots',
                'Test upgrade in a staging environment before production',
            ]
            if findings.get('summary', {}).get('crd_count', 0) > 0:
                reqs.append('Validate CRD conversion webhooks and storedVersions')
            if detected:
                reqs.append('Verify operator/controller compatibility and upgrade paths')

            console.print(Panel('\n'.join(['REQUIRED ACTIONS BEFORE UPGRADE:'] + [f"{i+1}. {r}" for i, r in enumerate(reqs)]), title='Required Actions', style='cyan'))

            # Recommended upgrade order
            console.print(Panel('1. Control Plane\n2. Nodes\n3. Workloads (if applicable)', title='Recommended Upgrade Order', style='green'))

            # Failure scenario analysis (conservative)
            failure_possible = readiness < 75
            fa = [
                ('Could workloads fail to start?', 'YES' if failure_possible else 'NO'),
                ('Could controllers crash?', 'YES' if failure_possible else 'NO'),
                ('Could CRDs become unreadable?', 'YES' if findings.get('summary', {}).get('crd_count', 0) > 0 else 'NO'),
                ('Could CRD controllers stop reconciling?', 'YES' if findings.get('summary', {}).get('crd_count', 0) > 0 else 'NO'),
                ('Could admission webhooks block deployments?', 'YES' if 'validatingwebhooks' in findings.get('risk_matrix', {}) or 'mutatingwebhooks' in findings.get('risk_matrix', {}) else 'NO'),
                ('Could storage become inaccessible?', 'YES' if 'Storage' in findings.get('risk_matrix', {}) and findings['risk_matrix']['Storage'].get('status') not in ('PASS', 'GOOD') else 'NO'),
                ('Could networking break?', 'YES' if 'Networking' in findings.get('risk_matrix', {}) and findings['risk_matrix']['Networking'].get('status') not in ('PASS', 'GOOD') else 'NO'),
                ('Could node upgrades fail?', 'YES' if readiness < 70 else 'NO'),
                ('Could kubelets fail to register?', 'YES' if readiness < 70 else 'NO'),
                ('Could the control plane fail?', 'YES' if readiness < 60 else 'NO'),
            ]
            console.print(Panel('\n'.join([f"- **{q}** {a}" for q, a in fa]), title='Failure Scenario Analysis', style='magenta'))

            # Risk Matrix table
            rm = Table(title='Risk Matrix', box=box.SIMPLE_HEAVY)
            rm.add_column('Area')
            rm.add_column('Status')
            rm.add_column('Severity')
            rm.add_column('Explanation')
            for area, v in findings.get('risk_matrix', {}).items():
                rm.add_row(area, v.get('status') or 'UNKNOWN', v.get('severity') or 'Medium', v.get('explanation') or '')
            console.print(rm)

        print_professional_summary(findings)

        # Final concise Cluster Summary including the computed readiness score
        try:
            final_cluster = summarize_cluster(outdir)
            final_tbl = Table.grid(expand=False)
            final_tbl.add_column(justify='left')
            final_tbl.add_column(justify='left')
            final_tbl.add_row('Cluster Type:', final_cluster.get('managed_hint') or 'Unknown')
            final_tbl.add_row('Kubernetes Version:', final_cluster.get('kubernetes_version') or 'N/A')
            final_tbl.add_row('Target Version:', args.target or 'N/A')
            final_tbl.add_row('Node Count:', str(final_cluster.get('node_count') or 'N/A'))
            final_tbl.add_row('Control Plane:', final_cluster.get('control_plane') or 'Unknown')
            readiness_val = findings.get('summary', {}).get('readiness')
            final_tbl.add_row('Readiness Score:', f"{readiness_val}/100" if readiness_val is not None else 'N/A')
            console.print(Panel(final_tbl, title='Final Cluster Summary', style='green'))
        except Exception as e:
            console.log(f'Failed to print final cluster summary: {e}')

        # End of assessment display
=======
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
>>>>>>> b4f0b28606631623f461d69b0cb8b00b578c85d3

    except Exception as e:
        console.log(f'Assessor run failed or assessor package not available: {e}')


if __name__ == "__main__":
    main()
