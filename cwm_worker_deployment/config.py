import os


CWM_WORKER_DEPLOYMENT_HELM_CACHE_DIR = os.environ.get("CWM_WORKER_DEPLOYMENT_HELM_CACHE_DIR") or "/var/cache/cwm-worker-deployment-helm-cache"
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL") or "http://localhost:9090"

DEPLOYMENT_TYPES = {
    "minio": {
        "hostname": "minio.{namespace_name}.svc.cluster.local",
        "readiness_checks": [
            {
                "type": "deployment",
                "deployment_name": "minio"
            }
        ],
        "metrics_checks": [
            *[
                {
                    "name": "network_receive_bytes_total_last_{}".format(d),
                    "type": "namespace_prometheus_rate_query",
                    "query": 'sum(rate(container_network_receive_bytes_total{namespace="__NAMESPACE_NAME__",pod=~"minio-.*"}['+d+']))'
                } for d in ['5m', '10m', '30m', '1h', '3h', '6h', '12h', '24h', '48h', '72h', '96h']
            ],
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
