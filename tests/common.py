import os
import json
import time
import base64
import tempfile
import datetime
import subprocess
from contextlib import contextmanager

from cwm_worker_deployment import helm
from cwm_worker_deployment import config


PACKAGES_READER_GITHUB_USER = os.environ.get("PACKAGES_READER_GITHUB_USER")
PACKAGES_READER_GITHUB_TOKEN = os.environ.get("PACKAGES_READER_GITHUB_TOKEN")
PULL_SECRET = '{"auths":{"docker.pkg.github.com":{"auth":"__AUTH__"}}}'.replace("__AUTH__", base64.b64encode("{}:{}".format(PACKAGES_READER_GITHUB_USER, PACKAGES_READER_GITHUB_TOKEN).encode()).decode())


def wait_for_cmd(cmd, expected_returncode, ttl_seconds, error_msg, expected_output=None):
    start_time = datetime.datetime.now()
    while True:
        returncode, output = subprocess.getstatusoutput(cmd)
        if returncode == expected_returncode and (expected_output is None or expected_output == output):
            break
        if (datetime.datetime.now() - start_time).total_seconds() > ttl_seconds:
            print(output)
            raise Exception(error_msg)
        time.sleep(1)


def wait_for_func(func, expected_result, ttl_seconds, error_msg):
    start_time = datetime.datetime.now()
    while True:
        result = func()
        if result == expected_result:
            break
        if (datetime.datetime.now() - start_time).total_seconds() > ttl_seconds:
            print(result)
            raise Exception(error_msg)
        time.sleep(1)


def init_wait_namespace(namespace_name, delete=False):
    if delete:
        returncode, output = subprocess.getstatusoutput('kubectl get ns {}'.format(namespace_name))
        if returncode == 0:
            returncode, output = subprocess.getstatusoutput('kubectl delete ns {}'.format(namespace_name))
            assert returncode == 0, output
            wait_for_cmd('kubectl get ns {}'.format(namespace_name), 1, 30,
                         'waited too long for namespace to be deleted')
    returncode, output = subprocess.getstatusoutput('kubectl get ns {}'.format(namespace_name))
    if returncode == 1:
        returncode, output = subprocess.getstatusoutput('kubectl create ns {}'.format(namespace_name))
        assert returncode == 0, output
        wait_for_cmd('kubectl get ns {}'.format(namespace_name), 0, 30,
                     'waited too long for test namespace to be created')


@contextmanager
def init_wait_deploy_helm(namespace_name):
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
        kwargs = {
            "chart_repo": 'https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-minio'}
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
            lambda: ['{name}-{status}'.format(**r) for r in
                     json.loads(subprocess.getstatusoutput('helm -n {} ls -o json'.format(namespace_name))[1])],
            ['minio-deployed'], 30, 'waited too long for release to be deployed'
        )
        yield tmpdir
