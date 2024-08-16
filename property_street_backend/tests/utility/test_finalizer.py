import pytest


@pytest.fixture
def test_finalizer(request):
    def cleanup():
        print("\n***Cleaning up after test")
    request.addfinalizer(cleanup)
    return "***\nbefore test"

def test_example(test_finalizer):
    # Your test code here
    print(test_finalizer)
    assert True