DEPLOYMENT_TYPES = {
    "minio": {
        "readiness_checks": [
            {
                "type": "deployment",
                "deployment_name": "minio"
            }
        ]
    }
}
