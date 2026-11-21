# Gets widget requests from wherever they are stored, one at a time
# I'll use the strategy pattern here too (from CS5700: object oriented programming)

import logging

logger = logging.getLogger(__name__)


class RequestSourceInterface:
    # Base class for request source strategies
    def __init__(self):
        pass

    def getNextRequest(self):
        raise NotImplementedError

    def finishRequest(self):
        # Called after the last request from getNextRequest has been processed.
        # Does nothing by default, sources that need to clean up after processing override it
        pass

class S3RequestSourceStrategy(RequestSourceInterface):
    # Strategy for fetching widget requests from S3
    def __init__(self, s3Client, bucketName):
        self.s3Client = s3Client
        self.bucketName = bucketName

    def getNextRequest(self):
        # Returns the JSON text of the request with the smallest key and deletes it, or None if there are none

        # 1. list objects v2, only ask for one key
        response = self.s3Client.list_objects_v2(Bucket=self.bucketName, MaxKeys=1)
        if "Contents" not in response:
            return None
        key = response["Contents"][0]["Key"]

        # 2. read the request text
        object = self.s3Client.get_object(Bucket=self.bucketName, Key=key)
        text = object["Body"].read().decode("utf-8")

        # 3. delete the request so it is not processed again
        self.s3Client.delete_object(Bucket=self.bucketName, Key=key)
        logger.info("Got request %s from S3 bucket %s", key, self.bucketName)

        return text


class SQSRequestSourceStrategy(RequestSourceInterface):
    # Strategy for fetching widget requests from an SQS queue

    MAX_MESSAGES = 10   # the most SQS will return in one receive_message call
    WAIT_SECONDS = 20   # long polling, the most SQS allows

    def __init__(self, sqsClient, queueName, waitSeconds=WAIT_SECONDS):
        self.sqsClient = sqsClient
        self.queueName = queueName
        self.waitSeconds = waitSeconds


        # Look up the queue URL once, the user only gives us the name
        self.queueUrl = sqsClient.get_queue_url(QueueName=queueName)["QueueUrl"]
        self.cache = []
        self.currentReceiptHandle = None

    def getNextRequest(self):
        # Returns the body of the next message, or None if emtpy
        # Stays in the queue until finishRequest is called

        # 1. refill the cache if it's empty
        if len(self.cache) == 0:
            self.cache = self.receiveMessages()
            if len(self.cache) == 0:
                return None

        # 2. hand out the next cached message and remember its receipt handle for finishRequest
        message = self.cache.pop(0)
        self.currentReceiptHandle = message["ReceiptHandle"]
        logger.info("Got request message %s from SQS queue %s", message["MessageId"], self.queueName)
        return message["Body"]

    def finishRequest(self):
        # Delete the last message handed out
        if self.currentReceiptHandle is None:
            return
        self.sqsClient.delete_message(QueueUrl=self.queueUrl, ReceiptHandle=self.currentReceiptHandle)
        self.currentReceiptHandle = None

    def receiveMessages(self):
        # Ask SQS for a batch of messages using long polling
        response = self.sqsClient.receive_message(QueueUrl=self.queueUrl, MaxNumberOfMessages=self.MAX_MESSAGES, WaitTimeSeconds=self.waitSeconds)
        messages = response.get("Messages", [])
        logger.info("Received %d messages from SQS queue %s", len(messages), self.queueName)
        return messages
