import urllib3
import requests
from kubernetes import client, config, utils
from kubernetes.client.rest import ApiException

import cwm_worker_deployment.config


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


def init(namespace_name, dry_run=False):
    namespace_spec = {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": namespace_name,
            "labels": {
                "cwmc-prom-servicemonitors": "allow"
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
        for container in deployment.spec.template.spec.containers:
            if container.resources.limits:
                metrics['ram_limit_bytes'] += (available_replicas * int(utils.quantity.parse_quantity(container.resources.limits['memory'])))
            if container.resources.requests:
                metrics['ram_requests_bytes'] += (available_replicas * int(utils.quantity.parse_quantity(container.resources.requests['memory'])))
    return metrics
