import json
import requests
import datetime
import subprocess
import tempfile
from ruamel import yaml


def repo_add(chart_name, repo_url, dry_run=False):
    cmd = ["helm", "repo", "add", chart_name, repo_url]
    if dry_run:
        print(" ".join(cmd))
    else:
        subprocess.check_call(cmd)


def repo_update(dry_run=False):
    cmd = ["helm", "repo", "update"]
    if dry_run:
        print(" ".join(cmd))
    else:
        subprocess.check_call(cmd)


def get_latest_version(repo_url, chart_name):
    repo_index = yaml.safe_load(requests.get("{}/index.yaml".format(repo_url)).content)
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


# example timeout string: "5m0s"
def upgrade(release_name, chart_name, namespace_name, version, values, atomic_timeout_string=None, dry_run=False, chart_path=None):
    with tempfile.NamedTemporaryFile("w") as f:
        yaml.safe_dump(values, f)
        cmd = [
            "helm", "upgrade", "--install", "--namespace", namespace_name, "--version", version, "-f", f.name,
            release_name, chart_path if chart_path else chart_name
        ]
        if atomic_timeout_string:
            cmd += ["--atomic", "--timeout", atomic_timeout_string]
        if dry_run:
            cmd += ["--dry-run"]
        result = subprocess.run(cmd, stderr=subprocess.PIPE)
        if result.returncode == 0:
            return True
        else:
            if result.stderr.decode().startswith('Error: failed to download'):
                return False
            else:
                raise Exception(result.stderr.decode())


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
