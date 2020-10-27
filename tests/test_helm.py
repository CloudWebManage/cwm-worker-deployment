import os
import json
import shutil
import datetime
import tempfile
import subprocess
from glob import glob

from cwm_worker_deployment import helm
from cwm_worker_deployment import config

from .common import init_wait_namespace, PULL_SECRET, wait_for_func


def test_get_latest_version():
    latest_version = helm.get_latest_version(
        'https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-minio',
        'cwm-worker-deployment-minio'
    )
    version, datetimestring = latest_version.split('-')
    for i in version.split('.'):
        assert int(i) >= 0
    assert isinstance(datetime.datetime.strptime(datetimestring, "%Y%m%dT%H%M%S"), datetime.datetime)


def test_chart_cache_init():
    with tempfile.TemporaryDirectory() as tmpdir:
        config.CWM_WORKER_DEPLOYMENT_HELM_CACHE_DIR = tmpdir
        latest_version = helm.get_latest_version(
            'https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-minio',
            'cwm-worker-deployment-minio'
        )
        expected_chart_path = os.path.join(tmpdir, "cwm-worker-deployment-minio", latest_version, "cwm-worker-deployment-minio")
        shutil.rmtree(expected_chart_path, ignore_errors=True)
        chart_path = helm.chart_cache_init(
            'cwm-worker-deployment-minio', latest_version,
            'https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-minio'
        )
        assert chart_path == expected_chart_path
        assert set([os.path.basename(p) for p in glob(os.path.join(chart_path, "*"))]) == {'values.yaml', 'templates', 'Chart.yaml'}


def test_release():
    namespace_name = 'cwdtest'
    init_wait_namespace(namespace_name, delete=True)
    latest_version = helm.get_latest_version(
        'https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-minio',
        'cwm-worker-deployment-minio'
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        config.CWM_WORKER_DEPLOYMENT_HELM_CACHE_DIR = tmpdir
        values = {
            'cwm-worker-deployment': {
                'type': 'minio',
                'namespace': namespace_name
            },
            'minio': {
                'createPullSecret': PULL_SECRET,
                'service': {
                    'enabled': False
                }
            },
            'extraObjects': []
        }
        args = ['minio', 'minio', 'cwm-worker-deployment-minio', namespace_name, latest_version, values]
        kwargs = {"chart_repo": 'https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-minio'}
        returncode, stdout, stderr = helm.upgrade(*args, dry_run=True, dry_run_debug=False, **kwargs)
        assert returncode == 0
        assert stderr.strip() == ""
        assert "NAME: minio" in stdout
        assert "image: docker.pkg.github.com/cloudwebmanage/cwm-worker-deployment-minio/minio" in stdout
        returncode, stdout, stderr = helm.upgrade(*args, **kwargs)
        assert returncode == 0
        assert stderr.strip() == ""
        assert 'Release "minio" does not exist. Installing it now.' in stdout
        wait_for_func(
            lambda: ['{name}-{status}'.format(**r) for r in json.loads(subprocess.getstatusoutput('helm -n {} ls -o json'.format(namespace_name))[1])],
            ['minio-deployed'], 30, 'waited too long for release to be deployed'
        )
        release_details = helm.get_release_details(namespace_name, 'minio')
        assert set(release_details.keys()) == {'name', 'namespace', 'revision', 'updated', 'status', 'chart', 'app_version'}
        assert release_details['name'] == 'minio'
        release_history = helm.get_release_history(namespace_name, 'minio')
        assert len(release_history) == 1
        assert set(release_history[0].keys()) == {'revision', 'updated', 'status', 'chart', 'app_version', 'description'}
        assert release_history[0]['revision'] == 1
        assert helm.delete(namespace_name, 'minio', dry_run=True)
        assert helm.delete(namespace_name, 'minio')
        wait_for_func(
            lambda: json.loads(subprocess.getstatusoutput('helm -n {} ls -o json'.format(namespace_name))[1]),
            [], 30, 'waited too long for release to be deleted'
        )
