from cwm_worker_deployment import config
from cwm_worker_deployment import helm
from cwm_worker_deployment import namespace


def _get_release_name(namespace_name, deployment_type):
    return "{}-{}".format(deployment_type, namespace_name)


def _is_ready_deployment(namespace_name, deployment_type, readiness_check):
    return namespace.is_ready_deployment(namespace_name, readiness_check['deployment_name'])


def chart_cache_init(chart_name, version, deployment_type):
    chart_repo = "https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-{}".format(deployment_type)
    return helm.chart_cache_init(chart_name, version, chart_repo)


# example timeout string: "5m0s"
def deploy(spec, dry_run=False, atomic_timeout_string=None):
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
    namespace.init(namespace_name, dry_run=dry_run)
    returncode, stdout, stderr = helm.upgrade(
        release_name, repo_name, chart_name, namespace_name, version, spec, dry_run=dry_run,
        atomic_timeout_string=atomic_timeout_string, chart_path=chart_path, chart_repo=chart_repo
    )
    if returncode == 0:
        return stdout
    else:
        raise Exception("Helm upgrade failed (returncode={})\nsdterr=\n{}\nstdout=\n{}".format(returncode, stdout, stderr))


# example timeout string: "5m0s"
def delete(namespace_name, deployment_type, timeout_string=None, dry_run=False, delete_namespace=False):
    release_name = _get_release_name(namespace_name, deployment_type)
    helm.delete(namespace_name, release_name, timeout_string=timeout_string, dry_run=dry_run)
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
