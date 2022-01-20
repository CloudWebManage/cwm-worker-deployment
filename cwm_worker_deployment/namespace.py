import time

import urllib3
import datetime
import traceback

import requests

from kubernetes import client, config, utils
from kubernetes.client.rest import ApiException

import cwm_worker_deployment.config


# This should match the image in cwm_worker_operator deployments_manager
ALPINE_IMAGE = "alpine:3.15.0@sha256:21a3deaa0d32a8057914f36584b5288d2e5ecc984380bc0118285c70fa8c9300"


urllib3.disable_warnings()
try:
    config.load_incluster_config()
except config.ConfigException:
    try:
        config.load_kube_config()
    except config.ConfigException:
        raise Exception("Could not configure kubernetes python client")


coreV1Api = client.CoreV1Api()
appsV1Api = client.AppsV1Api()
apiClient = client.ApiClient()
batchV1Api = client.BatchV1Api()


def init(namespace_name, dry_run=False):
    namespace_spec = {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": namespace_name,
            "labels": {
                "cwmc-prom-servicemonitors": "allow",
                "cwmc-minio": "yes"
            }
        }
    }
    if dry_run:
        print(namespace_spec)
    else:
        try:
            coreV1Api.create_namespace(namespace_spec)
        except ApiException as e:
            if e.reason != "Conflict":
                raise


def delete(namespace_name, dry_run=False):
    if dry_run:
        print("delete namespace: {}".format(namespace_name))
    else:
        try:
            coreV1Api.delete_namespace(namespace_name)
        except ApiException as e:
            if e.reason != "Not Found":
                raise


def is_ready_deployment(namespace_name, deployment_name):
    try:
        return appsV1Api.read_namespaced_deployment_status(deployment_name, namespace_name).status.ready_replicas > 0
    except Exception:
        return False


def delete_deployment(namespace_name, deployment_name):
    try:
        appsV1Api.delete_namespaced_deployment(deployment_name, namespace_name)
    except ApiException as e:
        if e.reason != "Not Found":
            raise


def delete_data(namespace_name, delete_data_config):
    sub_path, volume = delete_data_config['subPath'], delete_data_config['volume']
    sub_path = sub_path.strip()
    assert len(sub_path) > 3
    job_name = 'delete-data'
    create_objects(namespace_name, [{
        'apiVersion': 'batch/v1',
        'kind': 'Job',
        'metadata': {
            'name': job_name
        },
        'spec': {
            'parallelism': 1,
            'completions': 1,
            'template': {
                'spec': {
                    'restartPolicy': 'Never',
                    'terminationGracePeriodSeconds': 0,
                    'tolerations': [
                        {"key": "cwmc-role", "operator": "Exists", "effect": "NoSchedule"}
                    ],
                    'containers': [{
                        'name': job_name,
                        'image': ALPINE_IMAGE,
                        'command': ['rm', '-rf', '/data/{}'.format(sub_path)],
                        'volumeMounts': [{
                            'name': 'data',
                            'mountPath': '/data'
                        }]
                    }],
                    'volumes': [{
                        'name': 'data',
                        **volume
                    }]
                }
            },
        }
    }])
    try:
        success = False
        start_time = datetime.datetime.now()
        while (datetime.datetime.now() - start_time).total_seconds() < 1800:
            time.sleep(1)
            try:
                job: client.V1Job = batchV1Api.read_namespaced_job_status(job_name, namespace_name)
                status: client.V1JobStatus = job.status
                if status.succeeded and status.succeeded >= 1:
                    success = True
                    break
                elif status.failed and status.failed >= 1:
                    break
            except:
                traceback.print_exc()
        assert success, 'failed to delete data'
    finally:
        batchV1Api.delete_namespaced_job(job_name, namespace_name, propagation_policy='Foreground')


def create_service(namespace_name, service):
    service_body = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": service["name"]},
        "spec": service["spec"]
    }
    try:
        coreV1Api.create_namespaced_service(namespace_name, service_body)
    except ApiException as e:
        if e.reason != "Conflict":
            raise


def create_objects(namespace_name, objects):
    for object in objects:
        try:
            utils.create_from_dict(apiClient, object, namespace=namespace_name)
        except utils.FailToCreateError as e:
            if any([a.reason != "AlreadyExists" and a.reason != "Conflict" for a in e.api_exceptions]):
                raise


def metrics_check_prometheus_rate_query(namespace_name, query, debug=False):
    query = query.replace("__NAMESPACE_NAME__", namespace_name)
    url = cwm_worker_deployment.config.PROMETHEUS_URL.strip("/") + "/api/v1/query"
    params = {"query": query}
    if debug:
        print(url)
        print(params)
    res = requests.get(url, params=params).json()
    if debug:
        print(res)
    value = 0.0
    if res['status'] == 'success' and res['data']['resultType'] == 'vector':
        for metric in res['data']['result']:
            value += float(metric['value'][1])
    return value


def get_kube_metrics(namespace_name):
    metrics = {
        'ram_requests_bytes': 0,
        'ram_limit_bytes': 0
    }
    for deployment in appsV1Api.list_namespaced_deployment(namespace_name).items:
        available_replicas = deployment.status.available_replicas
        if available_replicas:
            for container in deployment.spec.template.spec.containers:
                if container.resources:
                    if container.resources.limits and container.resources.limits.get('memory'):
                        metrics['ram_limit_bytes'] += (available_replicas * int(utils.quantity.parse_quantity(container.resources.limits['memory'])))
                    if container.resources.requests and container.resources.requests.get('memory'):
                        metrics['ram_requests_bytes'] += (available_replicas * int(utils.quantity.parse_quantity(container.resources.requests['memory'])))
    return metrics


def get_deployments(namespace_name):
    return [
        deployment.to_dict()
        for deployment
        in appsV1Api.list_namespaced_deployment(namespace_name).items
    ]


def get_pods(namespace_name):
    return [
        pod.to_dict()
        for pod
        in coreV1Api.list_namespaced_pod(namespace_name).items
    ]


def get_namespace(namespace_name):
    return coreV1Api.read_namespace(namespace_name).to_dict()
