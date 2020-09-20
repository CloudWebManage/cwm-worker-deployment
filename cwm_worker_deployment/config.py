import os


CWM_WORKER_DEPLOYMENT_HELM_CACHE_DIR = os.environ.get("CWM_WORKER_DEPLOYMENT_HELM_CACHE_DIR") or "/var/cache/cwm-worker-deployment-helm-cache"


DEPLOYMENT_TYPES = {
    "minio": {
        "hostname": "minio.{namespace_name}.svc.cluster.local",
        "readiness_checks": [
            {
                "type": "deployment",
                "deployment_name": "minio"
            }
        ],
        "deletions": [
            {
                "type": "deployment",
                "deployment_name": "minio"
            }
        ],
        "external_services": [
            {
                "name": "minio",
                "spec": {
                    "ports": [
                        {"name": "8080", "port": 8080},
                        {"name": "8443", "port": 8443}
                    ],
                    "selector": {
                        "app": "minio"
                    }
                }
            }
        ]
    }
}
