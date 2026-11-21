# Unit tests for requestSources.py

import boto3
import pytest
from moto import mock_aws

from requestSources import S3RequestSourceStrategy, SQSRequestSourceStrategy


def makeQueue():
    # Create a fake SQS client with an empty request queue (must be called inside mock_aws)
    # Returns the client and the queue URL
    sqsClient = boto3.client("sqs", region_name="us-east-1")
    queueUrl = sqsClient.create_queue(QueueName="test-requests")["QueueUrl"]
    return sqsClient, queueUrl


def countMessages(sqsClient, queueUrl):
    # Count messages still in the queue, including ones that are currently being processed
    attrs = sqsClient.get_queue_attributes(
        QueueUrl=queueUrl,
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    )["Attributes"]
    return int(attrs["ApproximateNumberOfMessages"]) + int(attrs["ApproximateNumberOfMessagesNotVisible"])


def makeBucket():
    # Create a fake S3 client with an empty request bucket (must be called inside mock_aws)
    s3Client = boto3.client("s3", region_name="us-east-1")
    s3Client.create_bucket(Bucket="test-requests")
    return s3Client


#----------------------------
# S3RequestSourceStrategy Tests
#----------------------------

def testGetNextRequestEmptyBucketReturnsNone():
    # Tests that an empty bucket returns None
    with mock_aws():
        s3Client = makeBucket()
        source = S3RequestSourceStrategy(s3Client, "test-requests")

        assert source.getNextRequest() is None


def testGetNextRequestReturnsTextAndDeletesIt():
    # Tests that a request's text is returned and the request is removed from the bucket
    with mock_aws():
        s3Client = makeBucket()
        s3Client.put_object(Bucket="test-requests", Key="1", Body='{"type": "create"}')
        source = S3RequestSourceStrategy(s3Client, "test-requests")

        text = source.getNextRequest()

        assert text == '{"type": "create"}'
        assert "Contents" not in s3Client.list_objects_v2(Bucket="test-requests")


def testGetNextRequestReturnsSmallestKeyFirst():
    # Tests that requests come back in key order, one at a time, then None when empty
    with mock_aws():
        s3Client = makeBucket()
        s3Client.put_object(Bucket="test-requests", Key="b", Body="second")
        s3Client.put_object(Bucket="test-requests", Key="c", Body="third")
        s3Client.put_object(Bucket="test-requests", Key="a", Body="first")
        source = S3RequestSourceStrategy(s3Client, "test-requests")

        assert source.getNextRequest() == "first"
        assert source.getNextRequest() == "second"
        assert source.getNextRequest() == "third"
        assert source.getNextRequest() is None

        
#----------------------------
# SQSRequestSourceStrategy Tests
#----------------------------

def testSQSLooksUpQueueUrlFromName():
    # Tests that the queue URL is found from just the queue name
    with mock_aws():
        sqsClient, queueUrl = makeQueue()
        source = SQSRequestSourceStrategy(sqsClient, "test-requests", waitSeconds=0)

        assert source.queueUrl == queueUrl


def testSQSUnknownQueueRaises():
    # Tests that a queue name that doesn't exist fails right away
    with mock_aws():
        sqsClient, queueUrl = makeQueue()

        with pytest.raises(Exception):
            SQSRequestSourceStrategy(sqsClient, "no-such-queue", waitSeconds=0)


def testSQSGetNextRequestEmptyQueueReturnsNone():
    # Tests that an empty queue returns None
    with mock_aws():
        sqsClient, queueUrl = makeQueue()
        source = SQSRequestSourceStrategy(sqsClient, "test-requests", waitSeconds=0)

        assert source.getNextRequest() is None



def testSQSMessageNotDeletedUntilFinishRequest():
    # Tests that the message stays in the queue until finishRequest is called
    with mock_aws():
        sqsClient, queueUrl = makeQueue()
        sqsClient.send_message(QueueUrl=queueUrl, MessageBody="request")
        source = SQSRequestSourceStrategy(sqsClient, "test-requests", waitSeconds=0)

        source.getNextRequest()
        assert countMessages(sqsClient, queueUrl) == 1

        source.finishRequest()
        assert countMessages(sqsClient, queueUrl) == 0


def testSQSFinishRequestWithNoRequestDoesNothing():
    # Tests that finishRequest before any request, or called twice, doesn't fail
    with mock_aws():
        sqsClient, queueUrl = makeQueue()
        sqsClient.send_message(QueueUrl=queueUrl, MessageBody="request")
        source = SQSRequestSourceStrategy(sqsClient, "test-requests", waitSeconds=0)

        source.finishRequest()
        source.getNextRequest()
        source.finishRequest()
        source.finishRequest()

        assert source.currentReceiptHandle is None
        assert countMessages(sqsClient, queueUrl) == 0



def testSQSReadsAtMostTenAtATime():
    # Tests that 15 messages take two receives (10 then 5) and all 15 come back exactly once
    with mock_aws():
        sqsClient, queueUrl = makeQueue()
        for i in range(15):
            sqsClient.send_message(QueueUrl=queueUrl, MessageBody=str(i))
        source = SQSRequestSourceStrategy(sqsClient, "test-requests", waitSeconds=0)

        # count how many times SQS is asked for messages
        receiveCalls = []
        originalReceive = source._receiveMessages
        def countingReceive():
            messages = originalReceive()
            receiveCalls.append(len(messages))
            return messages
        source._receiveMessages = countingReceive

        bodies = []
        for i in range(15):
            bodies.append(source.getNextRequest())
            source.finishRequest()

        assert receiveCalls == [10, 5]
        assert sorted(bodies, key=int) == [str(i) for i in range(15)]
        assert source.getNextRequest() is None
        assert countMessages(sqsClient, queueUrl) == 0
