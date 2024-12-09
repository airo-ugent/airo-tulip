from typing import List, Callable, Dict, Tuple, Type

from cyclonedds.domain import DomainParticipant
from cyclonedds.idl import IdlStruct
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.topic import Topic
from loguru import logger

class Subscriber:
    def __init__(self, topic_name: str, topic: Topic, reader: DataReader, callback: Callable[[IdlStruct], None]):
        self.topic_name = topic_name
        self.topic = topic
        self.reader = reader
        self.callback = callback

    def step(self):
        messages = self.reader.take()
        for message in messages:
            self.callback(message)


class CycloneParticipant:
    def __init__(self, dds_domain_id: int=129):
        """Initialize the CycloneParticipant.

        Args:
            dds_domain_id: The CycloneDDS domain id (default: 129)."""
        logger.info(f"Joining CycloneDDS domain with id {dds_domain_id}.")
        self._cyclone_dp = DomainParticipant(domain_id=dds_domain_id)

        self._cyclone_subscribers: List[Subscriber] = []
        self._cyclone_publishers: Dict[str, Tuple[Topic, DataWriter]] = {}

    def _subscribe(self, topic: str, topic_datatype: Type[IdlStruct], callback: Callable[[IdlStruct], None]):
        """Subscribe to a topic with a callback function."""
        cyclone_topic = Topic(self._cyclone_dp, topic, topic_datatype)
        reader = DataReader(self._cyclone_dp, cyclone_topic)

        self._cyclone_subscribers.append(Subscriber(topic, cyclone_topic, reader, callback))

    def _publish(self, topic: str, message: IdlStruct):
        """Publish a message to a topic."""
        if topic not in self._cyclone_publishers:
            logger.warning(f"Topic {topic} not registered.")
            return

        _, writer = self._cyclone_publishers[topic]
        writer.write(message)

    def _register_publisher(self, topic: str, topic_datatype: Type[IdlStruct]):
        """Register a publisher for a topic."""
        cyclone_topic = Topic(self._cyclone_dp, topic, topic_datatype)
        writer = DataWriter(self._cyclone_dp, cyclone_topic)

        self._cyclone_publishers[topic] = (cyclone_topic, writer)

    def step(self):
        """Update subscribers."""
        for subscriber in self._cyclone_subscribers:
            subscriber.step()