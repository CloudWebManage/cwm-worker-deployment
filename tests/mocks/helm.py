from cwm_worker_deployment import helm


class MockHelm:

    def __init__(self):
        self._upgrade_calls = []
        self._upgrade_call_returnvalue = (0, "OK", "")
        self._delete_calls = []
        self._release_details_returnvalues = {}
        self._release_history_returnvalues = {}

    # this method has no special external dependencies, so no need to mock it
    def get_latest_version(self, *args, **kwargs):
        return helm.get_latest_version(*args, **kwargs)

    def upgrade(self, *args, **kwargs):
        self._upgrade_calls.append((args, kwargs))
        return self._upgrade_call_returnvalue

    def delete(self, namespace_name, release_name, **kwargs):
        self._delete_calls.append({"namespace_name": namespace_name, "release_name": release_name, "kwargs": kwargs})

    def get_release_details(self, namespace_name, release_name):
        return self._release_details_returnvalues['{}-{}'.format(namespace_name, release_name)]

    def get_release_history(self, namespace_name, release_name):
        return self._release_history_returnvalues['{}-{}'.format(namespace_name, release_name)]
