import os
import json
import requests
import datetime
import subprocess
import tempfile
from ruamel import yaml

from cwm_worker_deployment import config


def get_latest_version(repo_url, chart_name):
    repo_index = yaml.safe_load(requests.get("{}/index.yaml".format(repo_url), timeout=15).content)
    latest_entry_datetime = None
    latest_entry_version = None
    for entry in repo_index['entries'][chart_name]:
        if entry['version'].startswith('0.0.0-'):
            entry_datetime = datetime.datetime.strptime(entry['version'].replace('0.0.0-', ''), '%Y%m%dT%H%M%S')
            if latest_entry_datetime is None or latest_entry_datetime < entry_datetime:
                latest_entry_datetime = entry_datetime
                latest_entry_version = entry['version']
    assert latest_entry_version, 'failed to find latest version ({} {})'.format(repo_url, chart_name)
    return latest_entry_version


def chart_cache_init(chart_name, version, chart_repo):
    chart_cache_path = os.path.join(config.CWM_WORKER_DEPLOYMENT_HELM_CACHE_DIR, chart_name, version)
    if not os.path.exists(chart_cache_path):
        cmd = ["helm", "pull", chart_name, "--repo", chart_repo, "--untar", "--untardir", chart_cache_path, "--version",
               version]
        subprocess.check_call(cmd)
    return os.path.join(chart_cache_path, chart_name)


# example timeout string: "5m0s"
def upgrade(release_name, repo_name, chart_name, namespace_name, version, values, atomic_timeout_string=None,
            dry_run=False, chart_path=None, chart_repo=None, dry_run_debug=True):
    if not chart_path:
        chart_path = chart_cache_init(chart_name, version, chart_repo)
    with tempfile.NamedTemporaryFile("w") as f:
        yaml.safe_dump(values, f)
        if dry_run and dry_run_debug:
            print(json.dumps(values))
        cmd = ["helm", "upgrade", "--install", "--namespace", namespace_name, "--version", version, "-f", f.name, release_name, chart_path]
        if atomic_timeout_string:
            cmd += ["--atomic", "--timeout", atomic_timeout_string]
        if dry_run:
            cmd += ["--dry-run"]
        result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        return result.returncode, result.stdout.decode(), result.stderr.decode()


def delete(namespace_name, release_name, timeout_string=None, dry_run=False):
    cmd = ["helm", "delete", "--namespace", namespace_name, release_name]
    if timeout_string:
        cmd += ["--timeout", timeout_string]
    if dry_run:
        cmd += ["--dry-run"]
    result = subprocess.run(cmd, stderr=subprocess.PIPE)
    if result.returncode == 0:
        return True
    else:
        if 'release: not found' in result.stderr.decode():
            return True
        else:
            raise Exception(result.stderr.decode())


def get_release_details(namespace_name, release_name):
    cmd = ["helm", "list", "--namespace", namespace_name, "--filter", "^{}$".format(release_name), "-o", "json"]
    items = json.loads(subprocess.check_output(cmd))
    assert len(items) == 1
    return items[0]


def get_release_history(namespace_name, release_name):
    cmd = ["helm", "history", "--namespace", namespace_name, release_name, "-o", "json"]
    return json.loads(subprocess.check_output(cmd))


def iterate_all_releases(release_name, max_per_page=256):
    assert max_per_page <= 256
    offset = 0
    while True:
        cmd = ["helm", "ls", "--all-namespaces", "--max", str(max_per_page), "--offset", str(offset), "--filter", release_name, "-o", "json"]
        items = json.loads(subprocess.check_output(cmd))
        if len(items) == 0:
            break
        for item in items:
            yield item
            offset += 1
