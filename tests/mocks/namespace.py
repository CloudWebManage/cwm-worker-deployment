class MockNamespace:

    def __init__(self):
        self._init_namespace_names = []
        self._create_service_calls = []
        self._create_objects_calls = []
        self._deleted_namespace_names = []
        self._deleted_deployments = []
        self._is_ready_deployment_returnvalues = {}
        self._metrics_check_prometheus_rate_query_returnvalues = {}
        self._deleted_data = []
        self._get_namespaces = {}
        self._get_pods = {}
        self._get_deployments = {}

    def init(self, namespace_name, dry_run=False):
        if not dry_run:
            self._init_namespace_names.append(namespace_name)

    def create_service(self, namespace_name, service):
        self._create_service_calls.append({"namespace_name": namespace_name, "service": service})

    def create_objects(self, namespace_name, objects):
        self._create_objects_calls.append({"namespace_name": namespace_name, "objects": objects})

    def delete(self, namespace_name, dry_run=False):
        if not dry_run:
            self._deleted_namespace_names.append(namespace_name)

    def delete_deployment(self, namespace_name, deployment_name, force_now=False):
        self._deleted_deployments.append("{}-{}".format(namespace_name, deployment_name))

    def is_ready_deployment(self, namespace_name, deployment_name):
        return self._is_ready_deployment_returnvalues.get('{}-{}'.format(namespace_name, deployment_name))

    def metrics_check_prometheus_rate_query(self, namespace_name, query):
        return self._metrics_check_prometheus_rate_query_returnvalues['{}-{}'.format(namespace_name, query)]

    def delete_data(self, namespace_name, delete_data_config):
        self._deleted_data.append((namespace_name, delete_data_config))

    def get_namespace(self, namespace_name):
        return self._get_namespaces[namespace_name]

    def get_pods(self, namespace_name):
        return self._get_pods[namespace_name]

    def get_deployments(self, namespace_name):
        return self._get_deployments[namespace_name]