import subprocess

import pytest
from kubernetes.client.rest import ApiException
from kubernetes.utils.create_from_yaml import FailToCreateError

from cwm_worker_deployment import namespace

from .common import wait_for_cmd, wait_for_func, init_wait_namespace


def _delete_wait_service(namespace_name, service_name):
    returncode, output = subprocess.getstatusoutput('kubectl -n {} get service {}'.format(namespace_name, service_name))
    if returncode == 0:
        subprocess.getstatusoutput('kubectl -n {} delete service {}'.format(namespace_name, service_name))
        wait_for_cmd('kubectl -n {} get service {}'.format(namespace_name, service_name), 1, 30,
                     'waited too long for existing service to be deleted')


def test_init_delete():
    namespace_name = 'cwdtest'
    returncode, output = subprocess.getstatusoutput('kubectl delete ns {}'.format(namespace_name))
    if returncode == 0:
        wait_for_cmd('kubectl get ns {}'.format(namespace_name), 1, 30,
                     'waited too long for test namespace to be deleted')
    namespace.init(namespace_name, dry_run=True)
    namespace.init(namespace_name)
    returncode, output = subprocess.getstatusoutput('kubectl get ns {}'.format(namespace_name))
    assert returncode == 0, output
    namespace.init(namespace_name)
    returncode, output = subprocess.getstatusoutput('kubectl get ns {}'.format(namespace_name))
    assert returncode == 0, output
    namespace.delete(namespace_name, dry_run=True)
    namespace.delete(namespace_name)
    wait_for_cmd('kubectl get ns {}'.format(namespace_name), 1, 30,
                 'waited too long for namespace to be deleted')
    namespace.delete(namespace_name)
    returncode, output = subprocess.getstatusoutput('kubectl get ns {}'.format(namespace_name))
    assert returncode == 1, output


def test_is_ready_delete_deployment():
    namespace_name = 'cwdtest'
    init_wait_namespace(namespace_name)
    deployment_name = 'test'
    returncode, output = subprocess.getstatusoutput('kubectl -n {} get deployment {}'.format(namespace_name, deployment_name))
    if returncode == 0:
        subprocess.getstatusoutput('kubectl -n {} delete deployment {}'.format(namespace_name, deployment_name))
        wait_for_cmd('kubectl -n {} get deployment {}'.format(namespace_name, deployment_name), 1, 30,
                     'waited too long for existing deployment to be deleted')
    assert not namespace.is_ready_deployment(namespace_name, deployment_name)
    returncode, output = subprocess.getstatusoutput('kubectl -n {} create deployment {} --image=busybox -- sleep 86400'.format(
        namespace_name, deployment_name
    ))
    assert returncode == 0, output
    wait_for_func(lambda: namespace.is_ready_deployment(namespace_name, deployment_name), True, 30,
                  'waited too long for deployment to be ready')
    assert namespace.is_ready_deployment(namespace_name, deployment_name)
    namespace.delete_deployment(namespace_name, deployment_name)
    wait_for_func(lambda: namespace.is_ready_deployment(namespace_name, deployment_name), False, 30,
                  'waited too long for deployment to be deleted')
    returncode, output = subprocess.getstatusoutput('kubectl -n {} get deployment {}'.format(namespace_name, deployment_name))
    assert returncode == 1, output
    namespace.delete_deployment(namespace_name, deployment_name)
    returncode, output = subprocess.getstatusoutput('kubectl -n {} get deployment {}'.format(namespace_name, deployment_name))
    assert returncode == 1, output


def test_create_service():
    namespace_name = 'cwdtest'
    init_wait_namespace(namespace_name)
    service_name = 'test'
    _delete_wait_service(namespace_name, service_name)
    namespace.create_service(namespace_name, {
        'name': service_name,
        'spec': {'ports': [{'port': 80}]}
    })
    wait_for_cmd('kubectl -n {} get service {}'.format(namespace_name, service_name), 0, 30,
                 'waited too long for existing service to be created')
    with pytest.raises(ApiException):
        namespace.create_service(namespace_name, {
            'name': '__INVALID_SERVICE__',
            'spec': {}
        })


def test_create_objects():
    namespace_name = 'cwdtest'
    init_wait_namespace(namespace_name)
    service_name = 'test'
    _delete_wait_service(namespace_name, service_name + '1')
    _delete_wait_service(namespace_name, service_name + '2')
    namespace.create_objects(namespace_name, [
        {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': service_name + '1'
            },
            'spec': {'ports': [{'port': 80}]}
        },
        {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': service_name + '2'
            },
            'spec': {'ports': [{'port': 80}]}
        }
    ])
    wait_for_cmd('kubectl -n {} get service {}'.format(namespace_name, service_name + '1'), 0, 30,
                 'waited too long for existing service to be created')
    wait_for_cmd('kubectl -n {} get service {}'.format(namespace_name, service_name + '2'), 0, 30,
                 'waited too long for existing service to be created')
    with pytest.raises(FailToCreateError):
        namespace.create_objects(namespace_name, [
            {
                'apiVersion': 'v1',
                'kind': 'Service',
                'metadata': {
                    'name': service_name + '3'
                },
                'spec': {}
            }
        ])
