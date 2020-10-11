from ruamel import yaml

from cwm_worker_deployment import config
from cwm_worker_deployment import helm
from cwm_worker_deployment import namespace


def _get_release_name(namespace_name, deployment_type):
    return "{}-{}".format(deployment_type, namespace_name)


def _is_ready_deployment(namespace_name, deployment_type, readiness_check):
    return namespace.is_ready_deployment(namespace_name, readiness_check['deployment_name'])


def _delete_deployment(namespace_name, deployment_type, deletion):
    return namespace.delete_deployment(namespace_name, deletion['deployment_name'])


def chart_cache_init(chart_name, version, deployment_type):
    chart_repo = "https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-{}".format(deployment_type)
    return helm.chart_cache_init(chart_name, version, chart_repo)


def init(spec):
    spec = {**spec}
    deployment_spec = spec.pop('cwm-worker-deployment')
    deployment_type = deployment_spec["type"]
    assert deployment_type in config.DEPLOYMENT_TYPES, 'unknown deployment type: {}'.format(deployment_type)
    namespace_name = deployment_spec['namespace']
    namespace.init(namespace_name)


# example timeout string: "5m0s"
def deploy(spec, dry_run=False, atomic_timeout_string=None, with_init=True):
    spec = {**spec}
    deployment_spec = spec.pop('cwm-worker-deployment')
    deployment_type = deployment_spec["type"]
    assert deployment_type in config.DEPLOYMENT_TYPES, 'unknown deployment type: {}'.format(deployment_type)
    namespace_name = deployment_spec['namespace']
    release_name = _get_release_name(namespace_name, deployment_type)
    version = deployment_spec.get('version', 'latest')
    chart_path = deployment_spec.get('chart-path')
    if not chart_path and version == 'latest':
        version = helm.get_latest_version(
            "https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-{}".format(deployment_type),
            'cwm-worker-deployment-{}'.format(deployment_type)
        )
    chart_repo = "https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-{}".format(deployment_type)
    repo_name = "cwm-worker-deployment-{}".format(deployment_type)
    chart_name = "cwm-worker-deployment-{deployment_type}".format(deployment_type=deployment_type)
    if with_init:
        namespace.init(namespace_name, dry_run=dry_run)
    returncode, stdout, stderr = helm.upgrade(
        release_name, repo_name, chart_name, namespace_name, version, spec, dry_run=dry_run,
        atomic_timeout_string=atomic_timeout_string, chart_path=chart_path, chart_repo=chart_repo
    )
    if returncode == 0:
        return stdout
    else:
        raise Exception("Helm upgrade failed (returncode={})\nsdterr=\n{}\nstdout=\n{}".format(returncode, stdout, stderr))


def deploy_external_service(spec):
    spec = {**spec}
    deployment_spec = spec.pop('cwm-worker-deployment')
    deployment_type = deployment_spec["type"]
    assert deployment_type in config.DEPLOYMENT_TYPES, 'unknown deployment type: {}'.format(deployment_type)
    namespace_name = deployment_spec['namespace']
    for service in config.DEPLOYMENT_TYPES[deployment_type]["external_services"]:
        namespace.create_service(namespace_name, service)


def deploy_extra_objects(spec, extra_objects):
    namespace_name = spec['cwm-worker-deployment']['namespace']
    objects = []
    for object in extra_objects:
        objects.append({
            'apiVersion': object['apiVersion'],
            'kind': object['kind'],
            'metadata': {
                'name': object['name']
            },
            'spec': yaml.safe_load(object['spec'])
        })
    namespace.create_objects(namespace_name, objects)


# example timeout string: "5m0s"
def delete(namespace_name, deployment_type, timeout_string=None, dry_run=False, delete_namespace=False, delete_helm=True):
    release_name = _get_release_name(namespace_name, deployment_type)
    if delete_helm:
        helm.delete(namespace_name, release_name, timeout_string=timeout_string, dry_run=dry_run)
    else:
        for deletion in config.DEPLOYMENT_TYPES[deployment_type]["deletions"]:
            {
                "deployment": _delete_deployment
            }[deletion["type"]](namespace_name, deployment_type, deletion)
    if delete_namespace:
        namespace.delete(namespace_name, dry_run=dry_run)


def is_ready(namespace_name, deployment_type):
    for readiness_check in config.DEPLOYMENT_TYPES[deployment_type]["readiness_checks"]:
        res = {
            "deployment": _is_ready_deployment
        }[readiness_check["type"]](namespace_name, deployment_type, readiness_check)
        if not res:
            return False
    return True


def details(namespace_name, deployment_type):
    release_name = _get_release_name(namespace_name, deployment_type)
    release_details = helm.get_release_details(namespace_name, release_name)
    return {
        "name": release_name,
        "ready": is_ready(namespace_name, deployment_type),
        "app_version": release_details["app_version"],
        "chart": release_details["chart"],
        "revision": release_details["revision"],
        "status": release_details["status"],
        "updated": release_details["updated"]
    }


def history(namespace_name, deployment_type):
    release_name = _get_release_name(namespace_name, deployment_type)
    return helm.get_release_history(namespace_name, release_name)


def get_hostname(namespace_name, deployment_type):
    return config.DEPLOYMENT_TYPES[deployment_type]["hostname"].format(namespace_name=namespace_name)


if __name__ == '__main__':
    import sys
    if sys.argv[1] == 'test_deploy_extra_objects':
        namespace_name = sys.argv[2]
        mountScript = 'true'
        unmountScript = 'true'
        deploy_extra_objects({
            "cwm-worker-deployment": {
                "namespace": namespace_name
            }
        }, [
            {
                "apiVersion": "v1",
                "kind": "PersistentVolumeClaim",
                "name": namespace_name,
                "spec": """
accessModes: ["ReadWriteMany"]
resources: {"requests": {"storage": "1Ti"}}
storageClassName: ""
volumeMode: "Filesystem"
volumeName: "__NAMESPACE_NAME__"
""".replace('__NAMESPACE_NAME__', namespace_name)
            },
            {
                "apiVersion": "v1",
                "kind": "PersistentVolume",
                "name": namespace_name,
                "spec": """
accessModes: ["ReadWriteMany"]
capacity: {"storage": "1Ti"}
persistentVolumeReclaimPolicy: Delete
csi:
  driver: "shbs.csi.kamatera.com"
  volumeHandle: "__NAMESPACE_NAME__"
  volumeAttributes:
    mountScript: '__MOUNTSCRIPT__'
    unmountScript: '__UNMOUNTSCRIPT__'
""".replace('__MOUNTSCRIPT__', mountScript).replace('__UNMOUNTSCRIPT__', unmountScript).replace('__NAMESPACE_NAME__', namespace_name)
            }
        ])
