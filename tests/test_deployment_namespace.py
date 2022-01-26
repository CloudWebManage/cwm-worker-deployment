import time
import subprocess
from contextlib import contextmanager


from cwm_worker_deployment import namespace, deployment


@contextmanager
def get_namespace(extra_namespace_metadata=None, remove_finalizers=False):
    namespace_name = 'cwdt-deployment-namespace'
    if remove_finalizers:
        try:
            namespace.coreV1Api.patch_namespace(namespace_name, {'metadata': {'finalizers': None}})
        except:
            pass
    if subprocess.call(['kubectl', 'delete', '--wait', 'ns', namespace_name]) == 0:
        time.sleep(2)
    if not extra_namespace_metadata:
        extra_namespace_metadata = {}
    namespace.coreV1Api.create_namespace({
        'metadata': {
            'name': namespace_name,
            **extra_namespace_metadata
        }
    })
    time.sleep(1)
    try:
        yield namespace_name
    finally:
        if remove_finalizers:
            try:
                namespace.coreV1Api.patch_namespace(namespace_name, {'metadata': {'finalizers': None}})
            except:
                pass
        subprocess.call(['kubectl', 'delete', '--wait', 'ns', namespace_name])


def create_deployment(namespace_name, deployment_name, command=None, resources=None):
    if not command:
        command = ['sleep', '86400']
    if not resources:
        resources = {}
    namespace.appsV1Api.create_namespaced_deployment(namespace_name, {
        'metadata': {
            'name': deployment_name
        },
        'spec': {
            'selector': {
                'matchLabels': {
                    'app': deployment_name
                }
            },
            'template': {
                'metadata': {
                    'labels': {
                        'app': deployment_name
                    }
                },
                'spec': {
                    'terminationGracePeriodSeconds': 0,
                    'containers': [
                        {
                            'name': 'test',
                            'image': 'alpine',
                            'command': command,
                            'resources': resources,
                        }
                    ],
                }
            }
        }
    })


def assert_get_health(
        namespace_name,
        pod_name_starts_with=None, is_ready=None,
        namespace_phase=None,
        expected_health=None
):
    health = deployment.get_health(namespace_name, 'minio')
    for dn in health['deployments'].keys():
        for pod in health['deployments'][dn]['pods']:
            pod_name = pod.pop('name')
            assert pod_name
            if pod_name_starts_with:
                assert pod_name.startswith(pod_name_starts_with)
    if is_ready is not None:
        assert health.pop('is_ready') == is_ready
    assert health['namespace'].pop('name') == namespace_name
    if namespace_phase is not None:
        assert health['namespace'].pop('phase') == namespace_phase
        assert len(health['namespace']) == 0
        del health['namespace']
    if expected_health is not None:
        assert health == expected_health
    return health


def assert_get_health_multi(
        namespace_name, num_iterations, sleep_time_seconds: float = 1, pod_name_starts_with=None,
        namespace_phase=None
):
    healths = []
    for _ in range(num_iterations):
        time.sleep(sleep_time_seconds)
        healths.append(assert_get_health(
            namespace_name, pod_name_starts_with=pod_name_starts_with,
            namespace_phase=namespace_phase
        ))
    return healths


def test_get_health():
    with get_namespace() as namespace_name:
        base_name = 'test-namespace-test-get-deployment'
        deployment_names = ['{}{}'.format(base_name, i) for i in range(2)]
        for deployment_name in deployment_names:
            create_deployment(namespace_name, deployment_name)
        for deployment_name in deployment_names:
            subprocess.check_call([
                'kubectl', '-n', namespace_name, 'wait', '--for', 'condition=available', 'deployment', deployment_name
            ])
        assert_get_health(
            namespace_name,
            pod_name_starts_with=base_name,
            is_ready=False,
            namespace_phase='Active',
            expected_health={
                'deployments': {
                    'external-scaler': {'deployments': [], 'pods': []},
                    'logger': {'deployments': [], 'pods': []},
                    'nginx': {'deployments': [], 'pods': []},
                    'server': {'deployments': [], 'pods': []},
                    'unknown': {
                        'deployments': [
                            {
                                'name': 'test-namespace-test-get-deployment0',
                                'conditions': {
                                    'Available': 'True:MinimumReplicasAvailable',
                                    'Progressing': 'True:NewReplicaSetAvailable'
                                },
                                'replicas': {
                                    'available': 1,
                                    'ready': 1,
                                    'replicas': 1,
                                    'updated': 1
                                },
                            },
                            {
                                'name': 'test-namespace-test-get-deployment1',
                                'conditions': {
                                    'Available': 'True:MinimumReplicasAvailable',
                                    'Progressing': 'True:NewReplicaSetAvailable'
                                },
                                'replicas': {
                                    'available': 1,
                                    'ready': 1,
                                    'replicas': 1,
                                    'updated': 1
                                }
                            }
                        ],
                        'pods': [
                            {
                                'nodeName': 'minikube',
                                'phase': 'Running',
                                'conditions': {
                                    'ContainersReady': 'True',
                                    'Initialized': 'True',
                                    'PodScheduled': 'True',
                                    'Ready': 'True'
                                },
                                'containerStatuses': {
                                    'test': {
                                        'ready': True,
                                        'restartCount': 0,
                                        'started': True,
                                        'state': {
                                            'state': 'running'
                                        }
                                    }
                                },
                            },
                            {
                                'nodeName': 'minikube',
                                'phase': 'Running',
                                'conditions': {
                                    'ContainersReady': 'True',
                                    'Initialized': 'True',
                                    'PodScheduled': 'True',
                                    'Ready': 'True'
                                },
                                'containerStatuses': {
                                    'test': {
                                        'ready': True,
                                        'restartCount': 0,
                                        'started': True,
                                        'state': {
                                            'state': 'running'
                                        }
                                    }
                                },
                            }
                        ]
                    }
                },
            }
        )


def test_get_health_namespace_terminating():
    with get_namespace(
        extra_namespace_metadata={
            'finalizers': ['cwm-worker-deployment/tests']
        },
        remove_finalizers=True
    ) as namespace_name:
        subprocess.call(['kubectl', 'delete', '--timeout', '1s', 'ns', namespace_name])
        assert_get_health(
            namespace_name,
            is_ready=False,
            namespace_phase='Terminating',
        )


def test_get_health_pod_restart_loop():
    with get_namespace() as namespace_name:
        deployment_name = 'restarter'
        create_deployment(namespace_name, deployment_name, command=['false'])
        num_iterations = 20
        healths = assert_get_health_multi(
            namespace_name, 20, sleep_time_seconds=0.1, pod_name_starts_with=deployment_name,
        )
        deployments = [health['deployments']['unknown']['deployments'][0] for health in healths]
        assert len(deployments) == num_iterations
        for deployment in deployments:
            assert deployment == {
                'name': 'restarter',
                'conditions': {
                    'Available': 'False:MinimumReplicasUnavailable',
                    'Progressing': 'True:ReplicaSetUpdated'
                },
                'replicas': {
                    'available': None,
                    'ready': None,
                    'replicas': 1,
                    'updated': 1
                }
            }
        pods = [health['deployments']['unknown']['pods'][0] for health in healths]
        assert len(pods) == num_iterations
        num_pending, num_running = 0, 0
        for pod in pods:
            phase = pod.pop('phase')
            assert phase in ['Pending', 'Running']
            container_state = pod['containerStatuses']['test'].pop('state')
            if phase == 'Pending':
                num_pending += 1
                assert container_state == {
                    'state': 'waiting',
                    'reason': 'ContainerCreating'
                }
            elif phase == 'Running':
                num_running += 1
                assert container_state.pop('reason') in ['Error', 'CrashLoopBackOff']
                assert container_state.pop('state') in ['waiting', 'terminated']
                assert container_state.pop('exitCode', None) in [None, 1]
                assert container_state == {}
            assert pod['containerStatuses']['test'].pop('restartCount') >= 0
            assert pod == {
                'nodeName': 'minikube',
                'conditions': {
                    'ContainersReady': 'False:ContainersNotReady',
                    'Initialized': 'True',
                    'PodScheduled': 'True',
                    'Ready': 'False:ContainersNotReady'
                },
                'containerStatuses': {
                    'test': {
                        'ready': False,
                        'started': False,
                    }
                }
            }
        assert num_pending > 0
        assert num_running > 0
        assert num_pending + num_running == num_iterations


def test_get_health_pod_pending():
    with get_namespace() as namespace_name:
        deployment_name = 'pending'
        create_deployment(namespace_name, deployment_name, resources={
            'requests': {
                'memory': '1000Gi',
                'cpu': '100'
            }
        })
        healths = assert_get_health_multi(
            namespace_name, 5, pod_name_starts_with=deployment_name,
        )
        deployments = [health['deployments']['unknown']['deployments'][0] for health in healths]
        assert len(deployments) == 5
        for deployment in deployments:
            assert deployment == {
                'name': 'pending',
                'conditions': {
                    'Available': 'False:MinimumReplicasUnavailable',
                    'Progressing': 'True:ReplicaSetUpdated'
                },
                'replicas': {
                    'available': None,
                    'ready': None,
                    'replicas': 1,
                    'updated': 1
                }
            }
        pods = [health['deployments']['unknown']['pods'][0] for health in healths]
        assert len(pods) == 5
        for pod in pods:
            assert pod == {
                'nodeName': None,
                'phase': 'Pending',
                'conditions': {'PodScheduled': 'False:Unschedulable'},
                'containerStatuses': {}
            }
