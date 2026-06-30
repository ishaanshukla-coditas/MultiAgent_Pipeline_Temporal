"""
Standalone RabbitMQ consumer — completely independent of Temporal.
Subscribes to all pipeline events and reacts to them.

This is where you'd plug in real email, Slack, CMS, or analytics calls.
Right now it just logs, so you can see the messages arriving in real time.
"""
import asyncio
import json
import logging
import os
import aio_pika
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [consumer] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = "pipeline_events"


async def handle_event(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    async with message.process():
        data = json.loads(message.body)
        event = data.get("event", "unknown")
        topic = data.get("topic", "")
        title = data.get("title", "Untitled")

        if event == "article.ready":
            logger.info(f"📧  EMAIL  → '{title}' on '{topic}' is ready for review")
            logger.info(f"           Sending review link to editor@company.com")

        elif event == "article.approved":
            logger.info(f"✅  SLACK  → '{title}' approved and published!")
            logger.info(f"           Notifying #content-team channel")

        elif event == "article.rejected":
            feedback = data.get("feedback", "No feedback provided")
            logger.info(f"❌  SLACK  → '{title}' was rejected")
            logger.info(f"           Feedback to writer: {feedback}")

        else:
            logger.info(f"📨  EVENT  → {event}: {data}")


async def main() -> None:
    logger.info("Notification consumer starting — waiting for pipeline events...")

    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        exchange = await channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )

        # Durable queue so messages survive a consumer restart
        queue = await channel.declare_queue("notifications", durable=True)

        # article.* catches article.ready, article.approved, article.rejected
        await queue.bind(exchange, routing_key="article.*")

        logger.info("Subscribed to 'article.*' — listening...")
        await queue.consume(handle_event)

        await asyncio.Future()  # run forever


asyncio.run(main())
