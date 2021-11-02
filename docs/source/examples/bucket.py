import uprate as up
import asyncio

async def worker(id: int, bucket: up.Bucket[str]):
    async with bucket.acquire("GLOBAL_KEY"):
        # Lower the id longer the sleep
        await asyncio.sleep(0.4 + (4 - id)/100)
        print("hello from ", id)

async def main():
    # Bucket uses a queue so during creation a running loop must be present.
    bucket = up.Bucket[str](2 / up.Seconds(1), concurrency=2)
    await asyncio.gather(*(asyncio.create_task(worker(i, bucket)) for i in range(5)))

asyncio.run(main())

# Output:
# hello from  1
# hello from  0
# hello from  3
# hello from  2
# hello from  4