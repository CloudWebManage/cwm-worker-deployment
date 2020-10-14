import urllib3
from kubernetes import client, config, utils
from kubernetes.client.rest import ApiException


urllib3.disable_warnings()
try:
    config.load_incluster_config()
except config.ConfigException:
    try:
        config.load_kube_config()
    except config.ConfigException:
        raise Exception("Could not configure kubernetes python client")


codeV1Api = client.CoreV1Api()
appsV1Api = client.AppsV1Api()
apiClient = client.ApiClient()


def init(namespace_name, dry_run=False):
    namespace_spec = {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": namespace_name}}
    if dry_run:
        print(namespace_spec)
    else:
        try:
            codeV1Api.create_namespace(namespace_spec)
        except ApiException as e:
            if e.reason != "Conflict":
                raise


def delete(namespace_name, dry_run=False):
    if dry_run:
        print("delete namespace: {}".format(namespace_name))
    else:
        try:
            codeV1Api.delete_namespace(namespace_name)
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
        codeV1Api.create_namespaced_service(namespace_name, service_body)
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
