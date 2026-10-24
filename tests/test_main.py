# Unit tests for main.py

import json
import pytest
from main import parseArgs, processRequest


class FakeStore:
    # Records the widgets passed to create instead of talking to AWS
    def __init__(self):
        self.created = []

    def create(self, widget):
        self.created.append(widget)


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


def testProcessRequestUpdateAndDeleteAreSkipped():
    # Tests that update and delete requests do not store anything until assignment 7
    store = FakeStore()

    processRequest(makeRequestText("update"), store)
    processRequest(makeRequestText("delete"), store)

    assert store.created == []


def testProcessRequestBadJsonIsSkipped():
    # Tests that a bad request is logged and skipped instead of raising
    store = FakeStore()

    processRequest("{ this is not json", store)

    assert store.created == []


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
