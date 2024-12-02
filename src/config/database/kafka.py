# from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
# import json
# import os

# from dotenv import load_dotenv

# load_dotenv()

# KAFKA_SERVER = os.environ.get("KAFKA_SERVER")

# producer = AIOKafkaProducer(
#     bootstrap_servers=KAFKA_SERVER,  # type: ignore
#     value_serializer=lambda x: json.dumps(x).encode("utf-8"),
# )

# consumer = AIOKafkaConsumer(
#     "chat_messages",
#     bootstrap_servers=KAFKA_SERVER,  # type: ignore
#     value_deserializer=lambda x: json.loads(x.decode("utf-8")),
#     group_id="chat_group",
#     auto_offset_reset="latest",
# )
