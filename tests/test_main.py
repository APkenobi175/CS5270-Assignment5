# Unit tests for main.py

import json

import boto3
import pytest
from moto import mock_aws

from main import createSource, parseArgs, processNextRequest, processRequest
from requestSources import S3RequestSourceStrategy, SQSRequestSourceStrategy


class FakeStore:
    # Records what gets passed to each store method instead of talking to AWS
    def __init__(self, failWith=None):
        self.created = []
        self.updated = []
        self.deleted = []
        self.failWith = failWith

    def create(self, widget):
        if self.failWith is not None:
            raise self.failWith
        self.created.append(widget)

    def update(self, request):
        self.updated.append(request)

    def delete(self, request):
        self.deleted.append(request)


class FakeSource:
    # Hands out the given request texts and records how many times finishRequest was called
    def __init__(self, texts):
        self.texts = list(texts)
        self.finished = 0

    def getNextRequest(self):
        if len(self.texts) == 0:
            return None
        return self.texts.pop(0)

    def finishRequest(self):
        self.finished += 1


def makeRequestText(requestType):
    # Build the JSON text of a valid request with the given type
    return json.dumps({
        "type": requestType,
        "requestId": "req-1",
        "widgetId": "widget-1",
        "owner": "Ammon Phipps",
        "label": "My Label",
        "otherAttributes": [{"name": "color", "value": "red"}],
    })


#----------------------------
# processRequest Tests
#----------------------------

def testProcessRequestCreateStoresWidget():
    # Tests that a create request builds a widget and passes it to the store
    store = FakeStore()

    processRequest(makeRequestText("create"), store)

    assert len(store.created) == 1
    widget = store.created[0]
    assert widget.widgetId == "widget-1"
    assert widget.owner == "Ammon Phipps"
    assert widget.label == "My Label"
    assert widget.otherAttributes[0].name == "color"
    assert widget.otherAttributes[0].value == "red"


def testProcessRequestUpdateGoesToStoreUpdate():
    # Tests that an update request is passed to the store's update method
    store = FakeStore()

    processRequest(makeRequestText("update"), store)

    assert len(store.updated) == 1
    assert store.updated[0].widgetId == "widget-1"
    assert store.created == [] and store.deleted == []


def testProcessRequestDeleteGoesToStoreDelete():
    # Tests that a delete request is passed to the store's delete method
    store = FakeStore()

    processRequest(makeRequestText("delete"), store)

    assert len(store.deleted) == 1
    assert store.deleted[0].widgetId == "widget-1"
    assert store.created == [] and store.updated == []


def testProcessRequestBadJsonIsSkipped():
    # Tests that a bad request is logged and skipped instead of raising
    store = FakeStore()

    processRequest("{ this is not json", store)

    assert store.created == [] and store.updated == [] and store.deleted == []


#----------------------------
# processNextRequest Tests
#----------------------------

def testProcessNextRequestNoRequestReturnsFalse():
    # Tests that an empty source returns False and finishes nothing
    source = FakeSource([])

    assert processNextRequest(source, FakeStore()) is False
    assert source.finished == 0


def testProcessNextRequestProcessesAndFinishes():
    # Tests that a request is processed and then finished (removed from the source)
    source = FakeSource([makeRequestText("create")])
    store = FakeStore()

    assert processNextRequest(source, store) is True
    assert len(store.created) == 1
    assert source.finished == 1


def testProcessNextRequestBadRequestIsFinished():
    # Tests that a bad request is still finished so it doesn't keep coming back
    source = FakeSource(["{ this is not json"])

    assert processNextRequest(source, FakeStore()) is True
    assert source.finished == 1


def testProcessNextRequestStoreErrorIsNotFinished():
    # Tests that a store error is logged, doesn't crash, and leaves the request to be tried again
    source = FakeSource([makeRequestText("create")])
    store = FakeStore(failWith=RuntimeError("AWS is down"))

    assert processNextRequest(source, store) is True
    assert source.finished == 0


#----------------------------
# parseArgs Tests
#----------------------------

def testParseArgsS3():
    # Tests that the s3 storage arguments are read correctly
    args = parseArgs(["--storage", "s3", "--request-bucket", "bucket2", "--widget-bucket", "bucket3"])

    assert args.storage == "s3"
    assert args.request_bucket == "bucket2"
    assert args.widget_bucket == "bucket3"


def testParseArgsDynamoDefaultsTable():
    # Tests that dynamodb storage defaults to the widgets table
    args = parseArgs(["--storage", "dynamodb", "--request-bucket", "bucket2"])

    assert args.storage == "dynamodb"
    assert args.table == "widgets"


def testParseArgsS3WithoutWidgetBucketFails():
    # Tests that s3 storage without a widget bucket is rejected
    with pytest.raises(SystemExit):
        parseArgs(["--storage", "s3", "--request-bucket", "bucket2"])


def testParseArgsRequestQueue():
    # Tests that a queue name can be given instead of a request bucket, and region defaults to us-east-1
    args = parseArgs(["--storage", "dynamodb", "--request-queue", "cs5270-requests"])

    assert args.request_queue == "cs5270-requests"
    assert args.request_bucket is None
    assert args.region == "us-east-1"


def testParseArgsBucketAndQueueFails():
    # Tests that giving both a request bucket and a request queue is rejected
    with pytest.raises(SystemExit):
        parseArgs(["--storage", "dynamodb", "--request-bucket", "bucket2", "--request-queue", "cs5270-requests"])


def testParseArgsNoRequestSourceFails():
    # Tests that leaving out both the request bucket and the request queue is rejected
    with pytest.raises(SystemExit):
        parseArgs(["--storage", "dynamodb"])


#----------------------------
# createSource Tests
#----------------------------

def testCreateSourceQueueGivesSQSStrategy():
    # Tests that --request-queue picks the SQS request source
    with mock_aws():
        boto3.client("sqs", region_name="us-east-1").create_queue(QueueName="cs5270-requests")
        args = parseArgs(["--storage", "dynamodb", "--request-queue", "cs5270-requests"])

        assert isinstance(createSource(args), SQSRequestSourceStrategy)


def testCreateSourceBucketGivesS3Strategy():
    # Tests that --request-bucket picks the S3 request source
    args = parseArgs(["--storage", "dynamodb", "--request-bucket", "bucket2"])

    assert isinstance(createSource(args), S3RequestSourceStrategy)
