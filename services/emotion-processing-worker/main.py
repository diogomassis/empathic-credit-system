import asyncio
import os
import nats
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
NATS_SUBJECT = "user.emotions.topic"
DURABLE_NAME = "processor"

async def main():
    logging.info(f"Connecting to NATS at {NATS_URL}...")
    nc = None
    try:
        nc = await nats.connect(NATS_URL, name="emotion_processing_worker")
        js = nc.jetstream()
        logging.info("Connection to NATS established.")
        sub = await js.subscribe(
            subject=NATS_SUBJECT,
            durable=DURABLE_NAME
        )
        logging.info(f"Waiting for messages on topic '{NATS_SUBJECT}'...")
        async for msg in sub.messages:
            try:
                logging.info(f"Received: {msg.data.decode()}")
                await msg.ack()
            except Exception as e:
                logging.error(f"Error processing message: {e}")
    except Exception as e:
        logging.critical(f"A critical error occurred: {e}")
    finally:
        if nc and nc.is_connected:
            logging.info("Closing connection to NATS...")
            await nc.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Service terminated.")
