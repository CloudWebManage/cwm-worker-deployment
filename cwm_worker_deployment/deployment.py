from ruamel import yaml

from cwm_worker_deployment import config
from cwm_worker_deployment import helm
from cwm_worker_deployment import namespace


def _get_release_name(namespace_name, deployment_type):
    return "{}-{}".format(deployment_type, namespace_name)


def _is_ready_deployment(namespace_name, deployment_type, readiness_check, namespace_lib):
    return namespace_lib.is_ready_deployment(namespace_name, readiness_check['deployment_name'])


def _get_metrics_namespace_prometheus_rate_query(namespace_name, deployment_type, metrics_check, namespace_lib):
    return namespace_lib.metrics_check_prometheus_rate_query(namespace_name, metrics_check['query'])


def _delete_deployment(namespace_name, deployment_type, deletion, namespace_lib):
    return namespace_lib.delete_deployment(namespace_name, deletion['deployment_name'])


def chart_cache_init(chart_name, version, deployment_type):
    chart_repo = "https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-{}".format(deployment_type)
    return helm.chart_cache_init(chart_name, version, chart_repo)


def init(spec, namespace_lib=None):
    if namespace_lib is None:
        namespace_lib = namespace
    spec = {**spec}
    deployment_spec = spec.pop('cwm-worker-deployment')
    deployment_type = deployment_spec["type"]
    assert deployment_type in config.DEPLOYMENT_TYPES, 'unknown deployment type: {}'.format(deployment_type)
    namespace_name = deployment_spec['namespace']
    namespace_lib.init(namespace_name)


def deploy_preprocess_specs(specs, helm_lib=None):
    if not helm_lib:
        helm_lib = helm
    helm_latest_versions = {}
    preprocess_results = {}
    for key, spec in specs.items():
        spec = {**spec}
        deployment_spec = spec.pop('cwm-worker-deployment')
        deployment_type = deployment_spec["type"]
        assert deployment_type in config.DEPLOYMENT_TYPES, 'unknown deployment type: {}'.format(deployment_type)
        if deployment_type == 'minio':
            spec.setdefault('minio', {})['serveSingleProtocolPerPod'] = True
        namespace_name = deployment_spec['namespace']
        release_name = _get_release_name(namespace_name, deployment_type)
        chart_repo = "https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-{}".format(deployment_type)
        repo_name = "cwm-worker-deployment-{}".format(deployment_type)
        chart_name = "cwm-worker-deployment-{deployment_type}".format(deployment_type=deployment_type)
        version = deployment_spec.get('version', 'latest')
        chart_path = deployment_spec.get('chart-path')
        if not chart_path:
            if version == 'latest':
                if deployment_type in helm_latest_versions:
                    version = helm_latest_versions[deployment_type]
                else:
                    version = helm_latest_versions[deployment_type] = helm_lib.get_latest_version(
                        "https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-{}".format(deployment_type),
                        'cwm-worker-deployment-{}'.format(deployment_type)
                    )
            chart_path = helm_lib.chart_cache_init(chart_name, version, chart_repo)
        preprocess_results[key] = namespace_name, release_name, repo_name, chart_name, version, spec, chart_path, chart_repo
    return preprocess_results


# example timeout string: "5m0s"
def deploy(spec, dry_run=False, atomic_timeout_string=None, with_init=True, namespace_lib=None,
           helm_lib=None, preprocess_result=None):
    if not namespace_lib:
        namespace_lib = namespace
    if not helm_lib:
        helm_lib = helm
    if preprocess_result is None:
        preprocess_result = deploy_preprocess_specs({0: spec}, helm_lib=helm_lib)[0]
    namespace_name, release_name, repo_name, chart_name, version, spec, chart_path, chart_repo = preprocess_result
    if with_init:
        namespace_lib.init(namespace_name, dry_run=dry_run)
    returncode, stdout, stderr = helm_lib.upgrade(
        release_name, repo_name, chart_name, namespace_name, version, spec, dry_run=dry_run,
        atomic_timeout_string=atomic_timeout_string, chart_path=chart_path, chart_repo=chart_repo
    )
    if returncode == 0:
        return stdout
    else:
        raise Exception("Helm upgrade failed (returncode={})\nsdterr=\n{}\nstdout=\n{}".format(returncode, stdout, stderr))


def deploy_external_service(spec, namespace_lib=None):
    if not namespace_lib:
        namespace_lib = namespace
    spec = {**spec}
    deployment_spec = spec.pop('cwm-worker-deployment')
    deployment_type = deployment_spec["type"]
    assert deployment_type in config.DEPLOYMENT_TYPES, 'unknown deployment type: {}'.format(deployment_type)
    namespace_name = deployment_spec['namespace']
    for service in config.DEPLOYMENT_TYPES[deployment_type]["external_services"]:
        namespace_lib.create_service(namespace_name, service)


def deploy_extra_objects(spec, extra_objects, namespace_lib=None):
    if not namespace_lib:
        namespace_lib = namespace
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
    namespace_lib.create_objects(namespace_name, objects)


# example timeout string: "5m0s"
def delete(namespace_name, deployment_type, timeout_string=None, dry_run=False, delete_namespace=False, delete_helm=True, namespace_lib=None, helm_lib=None):
    if not namespace_lib:
        namespace_lib = namespace
    if not helm_lib:
        helm_lib = helm
    release_name = _get_release_name(namespace_name, deployment_type)
    if delete_helm:
        helm_lib.delete(namespace_name, release_name, timeout_string=timeout_string, dry_run=dry_run)
    else:
        for deletion in config.DEPLOYMENT_TYPES[deployment_type]["deletions"]:
            {
                "deployment": _delete_deployment
            }[deletion["type"]](namespace_name, deployment_type, deletion, namespace_lib)
    if delete_namespace:
        namespace_lib.delete(namespace_name, dry_run=dry_run)


def is_ready(namespace_name, deployment_type, namespace_lib=None, enabledProtocols=None, minimal_check=False):
    if not namespace_lib:
        namespace_lib = namespace
    if not enabledProtocols:
        enabledProtocols = ['http', 'https']
    for readiness_check in config.DEPLOYMENT_TYPES[deployment_type]["readiness_checks"]:
        if minimal_check and not readiness_check.get('minimal_check'):
            continue
        if readiness_check.get('protocol') and readiness_check['protocol'] not in enabledProtocols:
            continue
        res = {
            "deployment": _is_ready_deployment
        }[readiness_check["type"]](namespace_name, deployment_type, readiness_check, namespace_lib)
        if not res:
            return False
    return True


def get_metrics(namespace_name, deployment_type, namespace_lib=None):
    if not namespace_lib:
        namespace_lib = namespace
    metrics = {}
    for metrics_check in config.DEPLOYMENT_TYPES[deployment_type]["metrics_checks"]:
        metrics[metrics_check['name']] = {
            "namespace_prometheus_rate_query": _get_metrics_namespace_prometheus_rate_query
        }[metrics_check["type"]](namespace_name, deployment_type, metrics_check, namespace_lib)
    return metrics


def details(namespace_name, deployment_type, helm_lib=None, namespace_lib=None):
    if not helm_lib:
        helm_lib = helm
    if not namespace_lib:
        namespace_lib = namespace
    release_name = _get_release_name(namespace_name, deployment_type)
    release_details = helm_lib.get_release_details(namespace_name, release_name)
    return {
        "name": release_name,
        "ready": is_ready(namespace_name, deployment_type, namespace_lib=namespace_lib),
        "app_version": release_details["app_version"],
        "chart": release_details["chart"],
        "revision": release_details["revision"],
        "status": release_details["status"],
        "updated": release_details["updated"],
        "metrics": get_metrics(namespace_name, deployment_type, namespace_lib=namespace_lib),
    }


def history(namespace_name, deployment_type, helm_lib=None):
    if not helm_lib:
        helm_lib = helm
    release_name = _get_release_name(namespace_name, deployment_type)
    return helm_lib.get_release_history(namespace_name, release_name)


def get_hostname(namespace_name, deployment_type, protocol):
    return config.DEPLOYMENT_TYPES[deployment_type]["hostname"][protocol].format(namespace_name=namespace_name)


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
