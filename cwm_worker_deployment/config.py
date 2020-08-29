DEPLOYMENT_TYPES = {
    "minio": {
        "hostname": "minio.{namespace_name}.svc.cluster.local",
        "readiness_checks": [
            {
                "type": "deployment",
                "deployment_name": "minio"
            }
        ]
    }
}
