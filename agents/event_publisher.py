import json
import logging
import os
import aio_pika
from temporalio import activity

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = "pipeline_events"


@activity.defn
async def publish_pipeline_event(event_type: str, payload: dict) -> None:
    """
    Temporal activity that fires a message into RabbitMQ.
    The workflow calls this and immediately moves on — it does NOT wait
    for any consumer to read the message. This is the handoff point
    between Temporal (orchestration) and RabbitMQ (broadcasting).
    """
    logger.info(f"[rabbitmq] publishing → {event_type}")

    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )
        body = json.dumps({"event": event_type, **payload}).encode()
        await exchange.publish(
            aio_pika.Message(body=body, content_type="application/json"),
            routing_key=event_type,
        )

    logger.info(f"[rabbitmq] published → {event_type}")
