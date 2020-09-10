#!/usr/bin/env bash

echo deploying deployment with specific minio version &&\
NAMESPACE=specific-minio-version &&\
VERSION=0.0.0-20200829T091900 &&\
echo '
cwm-worker-deployment:
  type: minio
  namespace: "'"${NAMESPACE}"'"
  version: "'"${VERSION}"'"
minio:
  createPullSecret: |
    '${PULL_SECRET}'
' | cwm_worker_deployment deploy &&\
echo waiting for deployment to be ready &&\
tests/wait_for.sh "cwm_worker_deployment is_ready $NAMESPACE minio" "30" "watied too long for simple deployment to be ready" &&\
echo getting deployment details &&\
DEPLOYMENT_DETAILS="$(cwm_worker_deployment details $NAMESPACE minio | tee /dev/stderr)" &&\
echo "${DEPLOYMENT_DETAILS}" | grep "app_version: 303a65ed01c714ba7e0fe5b7aabecc519759d1c2" &&\
echo "${DEPLOYMENT_DETAILS}" | grep "chart: cwm-worker-deployment-minio-${VERSION}" &&\
echo getting deployment history &&\
cwm_worker_deployment history $NAMESPACE minio &&\
echo getting deployment hostname &&\
[ "$(cwm_worker_deployment get_hostname $NAMESPACE minio)" == "minio.$NAMESPACE.svc.cluster.local" ] &&\
echo deleting deployment &&\
cwm_worker_deployment delete $NAMESPACE minio --delete-namespace &&\
echo waiting for namespace to be deleted &&\
tests/wait_for.sh "! kubectl get ns $NAMESPACE" "30" "waited too long for namesapce to be deleted"
