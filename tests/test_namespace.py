import subprocess
from textwrap import dedent

import pytest
from kubernetes.client.rest import ApiException
from kubernetes.utils.create_from_yaml import FailToCreateError

from cwm_worker_deployment import namespace, config

from .common import wait_for_cmd, wait_for_func, init_wait_namespace, init_wait_deploy_helm


def _delete_wait_service(namespace_name, service_name):
    returncode, output = subprocess.getstatusoutput('kubectl -n {} get service {}'.format(namespace_name, service_name))
    if returncode == 0:
        subprocess.getstatusoutput('kubectl -n {} delete service {}'.format(namespace_name, service_name))
        wait_for_cmd('kubectl -n {} get service {}'.format(namespace_name, service_name), 1, 30,
                     'waited too long for existing service to be deleted')


def test_init_delete():
    namespace_name = 'cwdtest'
    returncode, output = subprocess.getstatusoutput('kubectl delete ns {}'.format(namespace_name))
    if returncode == 0:
        wait_for_cmd('kubectl get ns {}'.format(namespace_name), 1, 30,
                     'waited too long for test namespace to be deleted')
    namespace.init(namespace_name, dry_run=True)
    namespace.init(namespace_name)
    returncode, output = subprocess.getstatusoutput('kubectl get ns {}'.format(namespace_name))
    assert returncode == 0, output
    namespace.init(namespace_name)
    returncode, output = subprocess.getstatusoutput('kubectl get ns {}'.format(namespace_name))
    assert returncode == 0, output
    namespace.delete(namespace_name, dry_run=True)
    namespace.delete(namespace_name)
    wait_for_cmd('kubectl get ns {}'.format(namespace_name), 1, 30,
                 'waited too long for namespace to be deleted')
    namespace.delete(namespace_name)
    returncode, output = subprocess.getstatusoutput('kubectl get ns {}'.format(namespace_name))
    assert returncode == 1, output


def test_is_ready_delete_deployment():
    namespace_name = 'cwdtest'
    init_wait_namespace(namespace_name)
    deployment_name = 'test'
    returncode, output = subprocess.getstatusoutput('kubectl -n {} get deployment {}'.format(namespace_name, deployment_name))
    if returncode == 0:
        subprocess.getstatusoutput('kubectl -n {} delete deployment {}'.format(namespace_name, deployment_name))
        wait_for_cmd('kubectl -n {} get deployment {}'.format(namespace_name, deployment_name), 1, 30,
                     'waited too long for existing deployment to be deleted')
    assert not namespace.is_ready_deployment(namespace_name, deployment_name)
    returncode, output = subprocess.getstatusoutput('kubectl -n {} create deployment {} --image=busybox -- sleep 86400'.format(
        namespace_name, deployment_name
    ))
    assert returncode == 0, output
    wait_for_func(lambda: namespace.is_ready_deployment(namespace_name, deployment_name), True, 30,
                  'waited too long for deployment to be ready')
    assert namespace.is_ready_deployment(namespace_name, deployment_name)
    namespace.delete_deployment(namespace_name, deployment_name)
    wait_for_func(lambda: namespace.is_ready_deployment(namespace_name, deployment_name), False, 30,
                  'waited too long for deployment to be deleted')
    returncode, output = subprocess.getstatusoutput('kubectl -n {} get deployment {}'.format(namespace_name, deployment_name))
    assert returncode == 1, output
    namespace.delete_deployment(namespace_name, deployment_name)
    returncode, output = subprocess.getstatusoutput('kubectl -n {} get deployment {}'.format(namespace_name, deployment_name))
    assert returncode == 1, output


def test_create_service():
    namespace_name = 'cwdtest'
    init_wait_namespace(namespace_name)
    service_name = 'test'
    _delete_wait_service(namespace_name, service_name)
    namespace.create_service(namespace_name, {
        'name': service_name,
        'spec': {'ports': [{'port': 80}]}
    })
    wait_for_cmd('kubectl -n {} get service {}'.format(namespace_name, service_name), 0, 30,
                 'waited too long for existing service to be created')
    with pytest.raises(ApiException):
        namespace.create_service(namespace_name, {
            'name': '__INVALID_SERVICE__',
            'spec': {}
        })


def test_create_objects():
    namespace_name = 'cwdtest'
    init_wait_namespace(namespace_name)
    service_name = 'test'
    _delete_wait_service(namespace_name, service_name + '1')
    _delete_wait_service(namespace_name, service_name + '2')
    namespace.create_objects(namespace_name, [
        {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': service_name + '1'
            },
            'spec': {'ports': [{'port': 80}]}
        },
        {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': service_name + '2'
            },
            'spec': {'ports': [{'port': 80}]}
        }
    ])
    wait_for_cmd('kubectl -n {} get service {}'.format(namespace_name, service_name + '1'), 0, 30,
                 'waited too long for existing service to be created')
    wait_for_cmd('kubectl -n {} get service {}'.format(namespace_name, service_name + '2'), 0, 30,
                 'waited too long for existing service to be created')
    with pytest.raises(FailToCreateError):
        namespace.create_objects(namespace_name, [
            {
                'apiVersion': 'v1',
                'kind': 'Service',
                'metadata': {
                    'name': service_name + '3'
                },
                'spec': {}
            }
        ])


# we are not using the prometheus metrics at the moment
# @pytest.mark.filterwarnings("ignore:Unverified HTTPS request.*")
# def test_metrics_check_prometheus_rate_query():
#     namespace_name = 'cwdtest'
#     prompf = subprocess.Popen('exec kubectl port-forward service/prometheus-kube-prometheus-prometheus 9090', shell=True)
#     try:
#         time.sleep(2)
#         assert namespace.metrics_check_prometheus_rate_query(
#             "invalid--namespace",
#             config.DEPLOYMENT_TYPES['minio']['metrics_checks'][0]['query'],
#             debug=True
#         ) == 0.0
#         if os.environ.get("FULL_PROMETHEUS_TEST") == "yes":
#             with init_wait_deploy_helm(namespace_name) as tmpdir:
#                 print("Waiting for pods to be running...")
#                 wait_for_func(lambda: subprocess.getstatusoutput('kubectl -n cwdtest get pods | grep Running | wc -l')[1], "1", 60,
#                               "waited too long for pods to be running")
#                 print("Starting port forwards")
#                 http = subprocess.Popen('exec kubectl -n {} port-forward deployment/minio 8080:8080'.format(namespace_name), shell=True)
#                 https = subprocess.Popen('exec kubectl -n {} port-forward deployment/minio 8443:8443'.format(namespace_name), shell=True)
#                 time.sleep(2)
#                 try:
#                     print("Generating requests over a period of 2 minutes to gather metrics")
#                     for i in range(20):
#                         requests.get('http://localhost:8080/minio/login', headers={"User-Agent": "Mozilla"}, timeout=5)
#                         requests.get('https://localhost:8443/minio/login', headers={"User-Agent": "Mozilla"}, timeout=5, verify=False)
#                         time.sleep(6)
#                 finally:
#                     http.terminate()
#                     https.terminate()
#                 assert namespace.metrics_check_prometheus_rate_query(
#                     namespace_name,
#                     config.DEPLOYMENT_TYPES['minio']['metrics_checks'][0]['query'],
#                     debug=True
#                 ) > 10.0
#                 print("Sleeping 2 minutes to check no value for the network metrics..")
#                 time.sleep(120)
#                 query = config.DEPLOYMENT_TYPES['minio']['metrics_checks'][0]['query'].replace('5m', '1m')
#                 assert namespace.metrics_check_prometheus_rate_query(namespace_name, query, debug=True) == 0.0
#     finally:
#         prompf.terminate()


def test_delete_data():
    namespace_name = 'default'
    volume_config = {
        'hostPath': {
            'type': 'DirectoryOrCreate',
            'path': '/opt/cwm-worker-deployment/test_delete_data'
        }
    }
    pod_name = 'cwd-test-namespace-delete-data'
    namespace.create_objects(namespace_name, [{
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'name': pod_name
        },
        'spec': {
            'restartPolicy': 'Never',
            'terminationGracePeriodSeconds': 0,
            'containers': [{
                'name': pod_name,
                'image': namespace.ALPINE_IMAGE,
                'command': ['sleep', '86400'],
                'volumeMounts': [{
                    'name': 'data',
                    'mountPath': '/data'
                }]
            }],
            'volumes': [{
                'name': 'data',
                **volume_config
            }]
        }
    }])
    try:
        subprocess.check_call(['kubectl', '-n', namespace_name, 'wait', 'pod', pod_name, '--for', 'condition=Ready'])
        subpath = 'data'
        subprocess.check_call(['kubectl', '-n', namespace_name, 'exec', pod_name, '--', 'sh', '-c', dedent("""
            mkdir -p /data/{subpath} &&\
            touch /data/{subpath}/test1 &&\
            touch /data/{subpath}/test2.foo &&\
            touch /data/{subpath}/.test3
        """.format(subpath=subpath))])
        assert set(subprocess.check_output(['kubectl', '-n', namespace_name, 'exec', pod_name, '--', 'ls', '-a', '/data/{}'.format(subpath)]).decode().split()) == {
            '.', '..', '.test3', 'test1', 'test2.foo'}
        namespace.delete_data(namespace_name, {
            'subPath': subpath,
            'volume': volume_config
        })
        assert subprocess.call(['kubectl', '-n', namespace_name, 'exec', pod_name, '--', 'ls', '/data/{}'.format(subpath)]) == 1
    finally:
        namespace.coreV1Api.delete_namespaced_pod(pod_name, namespace_name)
