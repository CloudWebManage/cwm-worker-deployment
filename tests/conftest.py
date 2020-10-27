ORDERED_TESTS = [
    'tests/test_namespace.py',
    'tests/test_helm.py',
]


def pytest_collection_modifyitems(session, config, items):
    ordered_items = []
    for item in items:
        if item.location[0] not in ORDERED_TESTS:
            ordered_items.append(item)
    for item_location in ORDERED_TESTS:
        for item in items:
            if item.location[0] == item_location:
                ordered_items.append(item)
    items[:] = ordered_items
