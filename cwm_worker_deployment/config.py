import os


CWM_WORKER_DEPLOYMENT_HELM_CACHE_DIR = os.environ.get("CWM_WORKER_DEPLOYMENT_HELM_CACHE_DIR") or "/var/cache/cwm-worker-deployment-helm-cache"
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL") or "http://localhost:9090"

DEPLOYMENT_TYPES = {
    "minio": {
        "hostname": {
            'http': "minio-http.{namespace_name}.svc.cluster.local",
            'https': "minio-https.{namespace_name}.svc.cluster.local",
        },
        "readiness_checks": [
            {
                "type": "deployment",
                'protocol': 'http',
                "deployment_name": "minio-http"
            },
            {
                "type": "deployment",
                'protocol': 'https',
                "deployment_name": "minio-https"
            }
        ],
        "metrics_checks": [
            # the first query must be 5m network receive, otherwise test_namespace.test_metrics_check_prometheus_rate_query will break
            *[
                {
                    "name": "network_receive_bytes_total_last_{}".format(d),
                    "type": "namespace_prometheus_rate_query",
                    "query": 'rate(container_network_receive_bytes_total{namespace="__NAMESPACE_NAME__",pod=~"minio-(http|https)-.*"}['+d+'])'
                } for d in ['5m', '10m', '30m', '1h', '3h', '6h', '12h', '24h', '48h', '72h', '96h']
            ],
        ],
        "deletions": [
            {
                "type": "deployment",
                "deployment_name": "minio-http"
            },
            {
                "type": "deployment",
                "deployment_name": "minio-https"
            }
        ],
        "external_services": [
            {
                "name": "minio-http",
                "spec": {
                    "ports": [
                        {"name": "8080", "port": 8080}
                    ],
                    "selector": {
                        "app": "minio-http"
                    }
                }
            },
            {
                "name": "minio-https",
                "spec": {
                    "ports": [
                        {"name": "8443", "port": 8443}
                    ],
                    "selector": {
                        "app": "minio-https"
                    }
                }
            }
        ]
    }
}
