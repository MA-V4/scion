import asyncio
from evaluation.safety.adversarial import AdversarialEvaluator


async def main():
    evaluator = AdversarialEvaluator()
    report = await evaluator.run()
    report.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
