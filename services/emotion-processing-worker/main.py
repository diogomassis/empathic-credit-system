import asyncio
import os
import nats
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
NATS_SUBJECT = "user.emotions.topic"
STREAM_NAME = "emotions"

async def main():
    logging.info(f"Connecting to NATS at {NATS_URL}...")
    try:
        nc = await nats.connect(NATS_URL, name="emotion_processing_worker")
        js = nc.jetstream()
        logging.info("Connection to NATS established.")
        sub = await js.subscribe(subject=NATS_SUBJECT, durable="processing_worker")

        logging.info(f"Waiting for messages on topic '{NATS_SUBJECT}'...")
        async for msg in sub.messages:
            try:
                logging.info(f"Received: {msg.data.decode()}")
                await msg.ack()
            except Exception as e:
                logging.error(f"Error processing message: {e}")
    except Exception as e:
        logging.critical(f"Could not connect or subscribe to NATS: {e}")
    finally:
        if 'nc' in locals() and nc.is_connected:
            await nc.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Service terminated.")
