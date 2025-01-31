import pytest
import asyncio

@pytest.fixture
async def test_finalizer(request):
    async def cleanup():
        print("\nCleaning up after test")
        # Simulate async cleanup operation if needed
        await asyncio.sleep(1)

    request.addfinalizer(lambda: asyncio.run(cleanup()))
    return "\nBefore test"




@pytest.mark.asyncio
async def test_example(test_finalizer):
    # Your test code here
    result = await test_finalizer
    print(result)
    assert True
