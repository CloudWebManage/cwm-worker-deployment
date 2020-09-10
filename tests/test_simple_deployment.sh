#!/usr/bin/env bash

echo deploying simple deployment test1 &&\
eval "$(curl https://raw.githubusercontent.com/CloudWebManage/cwm-worker-helm/master/cwm-worker-deployment-minio/index.yaml | python3 -c "
import sys, datetime
appVersion = None
version = None
versions = []
for line in sys.stdin.readlines():
  line = line.strip()
  if line.startswith('appVersion: '):
    appVersion = line.replace('appVersion: ', '')
  if line.startswith('version: '):
    version = line.replace('version: ', '')
  if appVersion and version:
    versions.append([version, appVersion])
    appVersion = None
    version = None
latest_dt = None
latest_version = None
latest_appVersion = None
for v in versions:
  version, appVersion = v
  try:
    dt = datetime.datetime.strptime(version.split('-')[1], '%Y%m%dT%H%M%S')
  except Exception:
    dt = None
  if dt:
    if not latest_dt or latest_dt < dt:
      latest_dt = dt
      latest_version = version
      latest_appVersion = appVersion
print('LATEST_VERSION={}'.format(latest_version))
print('LATEST_APPVERSION={}'.format(latest_appVersion))
")" &&\
echo LATEST_VERSION=$LATEST_VERSION &&\
echo LATEST_APPVERSION=$LATEST_APPVERSION &&\
echo '
cwm-worker-deployment:
  type: minio
  namespace: test1
minio:
  createPullSecret: |
    '${PULL_SECRET}'
' | cwm_worker_deployment deploy &&\
echo waiting for deployment to be ready &&\
tests/wait_for.sh "cwm_worker_deployment is_ready test1 minio" "30" "watied too long for simple deployment to be ready" &&\
echo getting deployment details &&\
DEPLOYMENT_DETAILS="$(cwm_worker_deployment details test1 minio | tee /dev/stderr)" &&\
echo "${DEPLOYMENT_DETAILS}" | grep "app_version: ${LATEST_APPVERSION}" &&\
echo "${DEPLOYMENT_DETAILS}" | grep "chart: cwm-worker-deployment-minio-${LATEST_VERSION}" &&\
echo getting deployment history &&\
cwm_worker_deployment history test1 minio &&\
echo getting deployment hostname &&\
[ "$(cwm_worker_deployment get_hostname test1 minio)" == "minio.test1.svc.cluster.local" ] &&\
echo deleting deployment &&\
cwm_worker_deployment delete test1 minio --delete-namespace &&\
echo waiting for namespace to be deleted &&\
tests/wait_for.sh "! kubectl get ns test1" "30" "waited too long for namesapce to be deleted"
