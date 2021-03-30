import os
import shutil
import tempfile
from glob import glob

import pytest

from cwm_worker_deployment import config
from cwm_worker_deployment import deployment

from .mocks.namespace import MockNamespace
from .mocks.helm import MockHelm


def _set_namespace_metrics(namespace):
    for i, metrics_check in enumerate(config.DEPLOYMENT_TYPES['minio']['metrics_checks']):
        if metrics_check['type'] == 'namespace_prometheus_rate_query':
            namespace._metrics_check_prometheus_rate_query_returnvalues['test-{}'.format(metrics_check['query'])] = i


EXPECTED_NAMESPACE_METRICS = {
    'network_receive_bytes_total_last_10m': 1,
    'network_receive_bytes_total_last_12h': 6,
    'network_receive_bytes_total_last_1h': 3,
    'network_receive_bytes_total_last_24h': 7,
    'network_receive_bytes_total_last_30m': 2,
    'network_receive_bytes_total_last_3h': 4,
    'network_receive_bytes_total_last_48h': 8,
    'network_receive_bytes_total_last_5m': 0,
    'network_receive_bytes_total_last_6h': 5,
    'network_receive_bytes_total_last_72h': 9,
    'network_receive_bytes_total_last_96h': 10
}


def test_chart_cache_init():
    helm = MockHelm()
    with tempfile.TemporaryDirectory() as tmpdir:
        config.CWM_WORKER_DEPLOYMENT_HELM_CACHE_DIR = tmpdir
        latest_version = helm.get_latest_version(
            'https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-minio',
            'cwm-worker-deployment-minio'
        )
        expected_chart_path = os.path.join(tmpdir, "cwm-worker-deployment-minio", latest_version, "cwm-worker-deployment-minio")
        shutil.rmtree(expected_chart_path, ignore_errors=True)
        chart_path = deployment.chart_cache_init('cwm-worker-deployment-minio', latest_version, 'minio')
        assert chart_path == expected_chart_path
        assert set([os.path.basename(p) for p in glob(os.path.join(chart_path, "*"))]) == {
            'values.yaml', 'templates', 'Chart.yaml', 'cwm-worker-logger.image'}


def test_init():
    namespace = MockNamespace()
    spec = {
        'cwm-worker-deployment': {
            'type': '__INVALID__',
            'namespace': 'test'
        }
    }
    with pytest.raises(AssertionError):
        deployment.init(spec, namespace_lib=namespace)
    spec['cwm-worker-deployment']['type'] = 'minio'
    deployment.init(spec, namespace_lib=namespace)
    assert namespace._init_namespace_names == ['test']


def test_deploy():
    namespace = MockNamespace()
    helm = MockHelm()
    spec = {
        'cwm-worker-deployment': {
            'type': '__INVALID__',
            'namespace': 'test'
        }
    }
    with pytest.raises(AssertionError):
        deployment.deploy(spec, namespace_lib=namespace, helm_lib=helm)
    spec['cwm-worker-deployment']['type'] = 'minio'
    assert deployment.deploy(spec, namespace_lib=namespace, helm_lib=helm) == "OK"
    assert len(helm._upgrade_calls) == 1
    assert helm._upgrade_calls[0][0][0] == 'minio-test'
    helm = MockHelm()
    helm._upgrade_call_returnvalue = (1, "ERROR", "error")
    with pytest.raises(Exception):
        deployment.deploy(spec, namespace_lib=namespace, helm_lib=helm)


def test_deploy_external_service():
    namespace = MockNamespace()
    spec = {
        'cwm-worker-deployment': {
            'type': '__INVALID__',
            'namespace': 'test'
        }
    }
    with pytest.raises(AssertionError):
        deployment.deploy_external_service(spec, namespace_lib=namespace)
    spec['cwm-worker-deployment']['type'] = 'minio'
    deployment.deploy_external_service(spec, namespace_lib=namespace)
    assert namespace._create_service_calls == [
        {
            'namespace_name': 'test',
            'service': {
                'name': 'minio-http',
                'spec': {
                    'ports': [
                        {'name': '8080', 'port': 8080}
                    ],
                    'selector': {'app': 'minio-http'}
                }
            }
        },
        {
            'namespace_name': 'test',
            'service': {
                'name': 'minio-https',
                'spec': {
                    'ports': [
                        {'name': '8443', 'port': 8443}
                    ],
                    'selector': {'app': 'minio-https'}
                }
            }
        }
    ]


def test_deploy_extra_objects():
    namespace = MockNamespace()
    spec = {
        'cwm-worker-deployment': {
            'namespace': 'test'
        }
    }
    deployment.deploy_extra_objects(spec, [{
        'apiVersion': 'v1',
        'kind': 'Service',
        'name': 'test-extra-object',
        'spec': 'ports:\n- name: "8080"\n  port: 8080\n  TargetPort: 8080\nselector:\n  app: minio'}
    ], namespace_lib=namespace)
    assert namespace._create_objects_calls == [{
        'namespace_name': 'test',
        'objects': [{
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {'name': 'test-extra-object'},
            'spec': {'ports': [{'TargetPort': 8080, 'name': '8080', 'port': 8080}], 'selector': {'app': 'minio'}}
        }]
    }]


def test_delete():
    namespace = MockNamespace()
    helm = MockHelm()
    deployment.delete('test', 'minio', namespace_lib=namespace, helm_lib=helm)
    assert helm._delete_calls == [{'kwargs': {'dry_run': False, 'timeout_string': None}, 'namespace_name': 'test', 'release_name': 'minio-test'}]
    assert namespace._deleted_namespace_names == []
    assert namespace._deleted_deployments == []
    namespace = MockNamespace()
    helm = MockHelm()
    deployment.delete('test', 'minio', namespace_lib=namespace, helm_lib=helm, delete_helm=False)
    assert helm._delete_calls == []
    assert namespace._deleted_namespace_names == []
    assert namespace._deleted_deployments == ['test-minio-http', 'test-minio-https']
    namespace = MockNamespace()
    helm = MockHelm()
    deployment.delete('test', 'minio', namespace_lib=namespace, helm_lib=helm, delete_helm=False, delete_namespace=True)
    assert helm._delete_calls == []
    assert namespace._deleted_namespace_names == ['test']
    assert namespace._deleted_deployments == ['test-minio-http', 'test-minio-https']


def test_is_ready():
    namespace = MockNamespace()
    namespace._is_ready_deployment_returnvalues['test-minio-http'] = True
    namespace._is_ready_deployment_returnvalues['test-minio-https'] = True
    assert deployment.is_ready('test', 'minio', namespace_lib=namespace)
    namespace = MockNamespace()
    namespace._is_ready_deployment_returnvalues['test-minio-http'] = False
    assert not deployment.is_ready('test', 'minio', namespace_lib=namespace)


def test_details():
    namespace = MockNamespace()
    _set_namespace_metrics(namespace)
    helm = MockHelm()
    helm._release_details_returnvalues['test-minio-test'] = {'app_version': 'app_version', 'chart': 'chart', 'revision': 'revision', 'status': 'status', 'updated': 'updated'}
    expected_deployment_details = {
        'name': 'minio-test',
        'ready': False,
        'app_version': 'app_version',
        'chart': 'chart',
        'revision': 'revision',
        'status': 'status',
        'updated': 'updated',
        'metrics': EXPECTED_NAMESPACE_METRICS
    }
    assert deployment.details('test', 'minio', helm_lib=helm, namespace_lib=namespace) == expected_deployment_details
    namespace._is_ready_deployment_returnvalues['test-minio-http'] = True
    assert deployment.details('test', 'minio', helm_lib=helm, namespace_lib=namespace) == expected_deployment_details
    namespace._is_ready_deployment_returnvalues['test-minio-https'] = True
    expected_deployment_details['ready'] = True
    assert deployment.details('test', 'minio', helm_lib=helm, namespace_lib=namespace) == expected_deployment_details


def test_history():
    helm = MockHelm()
    helm._release_history_returnvalues['test-minio-test'] = []
    assert deployment.history('test', 'minio', helm_lib=helm) == []


def test_get_hostname():
    assert deployment.get_hostname('test', 'minio', 'http') == 'minio-http.test.svc.cluster.local'
    assert deployment.get_hostname('test', 'minio', 'https') == 'minio-https.test.svc.cluster.local'


def test_get_metrics():
    namespace = MockNamespace()
    _set_namespace_metrics(namespace)
    assert deployment.get_metrics('test', 'minio', namespace_lib=namespace) == EXPECTED_NAMESPACE_METRICS
