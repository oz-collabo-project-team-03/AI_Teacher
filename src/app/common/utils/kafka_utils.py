# from src.config.database.kafka import producer, consumer

# async def create_async_kafka_producer():
#     await producer.start()
#     return producer


# async def create_async_kafka_consumer(topic, group_id):
#     await consumer.start()
#     return consumer


# async def consume_messages(consumer, message_handler):
#     try:
#         async for message in consumer:
#             await message_handler(message.value)
#     finally:
#         await consumer.stop()


# async def produce_message(producer, topic, message):
#     await producer.send_and_wait(topic, message)
