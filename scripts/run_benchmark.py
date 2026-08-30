import asyncio
import argparse
from evaluation.runners.benchmark import BenchmarkRunner


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="general", choices=["general", "scientific", "safety"])
    args = parser.parse_args()

    runner = BenchmarkRunner(suite=args.suite)
    runner.load_tasks()
    result = await runner.run()
    result.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
