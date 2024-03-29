import os
import json
import shutil
import datetime
import tempfile
import subprocess
from glob import glob

import pytest

from cwm_worker_deployment import helm
from cwm_worker_deployment import config

from .common import wait_for_func, init_wait_deploy_helm


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
        assert set([os.path.basename(p) for p in glob(os.path.join(chart_path, "*"))]) == {
            'values.yaml', 'templates', 'Chart.yaml', 'cwm-worker-logger.image', 'cwm-keda-external-scaler.image'}


def test_release():
    namespace_name = 'cwdtest'
    with init_wait_deploy_helm(namespace_name) as tmpdir:
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


@pytest.mark.skip('this test takes a long time and fails sometime, not worth to run for such a small feature')
def test_iterate_all_releases():
    with init_wait_deploy_helm("cwdtest") as tmpdir1:
        with init_wait_deploy_helm("cwdbest") as tmpdir2:
            assert set(
                [r["name"] + "-" + r["namespace"] for r in helm.iterate_all_releases("minio", max_per_page=1)]
            ) == {
                "minio-cwdtest", "minio-cwdbest"
            }
