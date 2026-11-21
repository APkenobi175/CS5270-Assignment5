# Unit tests for widgetStores.py

import json

import boto3
from moto import mock_aws

from models import OtherAttribute, Widget, WidgetRequest
from widgetStores import DynamoDBWidgetStoreStrategy, S3WidgetStoreStrategy


def makeWidget():
    # Build a widget with every field filled in
    return Widget("widget-1", "Ammon Phipps", "My Label", "My Description", [OtherAttribute("color", "red"), OtherAttribute("size", "large")])


def makeRequest(requestType, label=None, description=None, otherAttributes=None, widgetId="widget-1"):
    # Build an update or delete request for widget-1
    return WidgetRequest(requestType, "req-2", widgetId, "Ammon Phipps", label, description, otherAttributes)


def makeS3Store():
    # Create a fake S3 bucket and a store for it (must be called inside mock_aws)
    s3Client = boto3.client("s3", region_name="us-east-1")
    s3Client.create_bucket(Bucket="test-bucket")
    return s3Client, S3WidgetStoreStrategy(s3Client, "test-bucket")


def makeDynamoStore():
    # Create a fake DynamoDB table and a store for it (must be called inside mock_aws)
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.create_table(
        TableName="widgets",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    return table, DynamoDBWidgetStoreStrategy(table)


S3_KEY = "widgets/ammon-phipps/widget-1"


#----------------------------
# S3WidgetStoreStrategy Tests
#----------------------------

def testS3OwnerKeyReplacesSpacesAndLowercases():
    # Tests that owner names are lowercased and spaces become dashes
    store = S3WidgetStoreStrategy(None, "test-bucket")

    assert store._ownerKey("Ammon Taylor Phipps") == "ammon-taylor-phipps"


def testS3WidgetKey():
    # Tests that the widget key follows widgets/{owner}/{widgetId}
    store = S3WidgetStoreStrategy(None, "test-bucket")

    assert store._widgetKey(makeWidget()) == "widgets/ammon-phipps/widget-1"


def testS3CreateStoresWidgetJson():
    # Tests that create stores the widget's JSON at the expected key in a fake S3 bucket
    with mock_aws():
        s3Client = boto3.client("s3", region_name="us-east-1")
        s3Client.create_bucket(Bucket="test-bucket")
        store = S3WidgetStoreStrategy(s3Client, "test-bucket")
        widget = makeWidget()

        store.create(widget)

        obj = s3Client.get_object(Bucket="test-bucket", Key="widgets/ammon-phipps/widget-1")
        assert json.loads(obj["Body"].read()) == widget.toDict()


def testS3UpdateChangesStoredWidget():
    # Tests that update changes, removes, and adds fields on the stored widget
    with mock_aws():
        s3Client, store = makeS3Store()
        store.create(makeWidget())

        store.update(makeRequest("update", label="New Label", description="",
                                 otherAttributes=[OtherAttribute("color", "blue"), OtherAttribute("size", ""), OtherAttribute("weight", "heavy")]))

        obj = s3Client.get_object(Bucket="test-bucket", Key=S3_KEY)
        assert json.loads(obj["Body"].read()) == {
            "id": "widget-1",
            "owner": "Ammon Phipps",
            "label": "New Label",
            "description": None,
            "otherAttributes": [{"name": "color", "value": "blue"}, {"name": "weight", "value": "heavy"}],
        }


def testS3UpdateMissingWidgetWarns(caplog):
    # Tests that updating a widget that doesn't exist logs a warning and doesn't create it
    with mock_aws():
        s3Client, store = makeS3Store()

        store.update(makeRequest("update", label="New Label"))

        assert "Update failed" in caplog.text
        assert "Contents" not in s3Client.list_objects_v2(Bucket="test-bucket")


def testS3DeleteRemovesWidget():
    # Tests that delete removes the stored widget
    with mock_aws():
        s3Client, store = makeS3Store()
        store.create(makeWidget())

        store.delete(makeRequest("delete"))

        assert "Contents" not in s3Client.list_objects_v2(Bucket="test-bucket")


def testS3DeleteMissingWidgetWarns(caplog):
    # Tests that deleting a widget that doesn't exist logs a warning instead of raising
    with mock_aws():
        s3Client, store = makeS3Store()

        store.delete(makeRequest("delete"))

        assert "Delete failed" in caplog.text


#----------------------------
# DynamoDBWidgetStoreStrategy Tests
#----------------------------


def testDynamoToItemSkipsMissingOptionalFields():
    # Tests that a missing label and description are left out of the item
    store = DynamoDBWidgetStoreStrategy(None)

    item = store._toItem(Widget("widget-1", "Ammon Phipps"))

    assert item == {"id": "widget-1", "owner": "Ammon Phipps"}


def testDynamoCreateStoresItem():
    # Tests that create stores the flattened widget in a fake DynamoDB table fropm mock_aws in moto library
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="widgets",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        store = DynamoDBWidgetStoreStrategy(table)

        store.create(makeWidget())

        # Each other attribute (color, size) must be its own top-level attribute, not a list
        item = table.get_item(Key={"id": "widget-1"})["Item"]
        assert item == {
            "id": "widget-1",
            "owner": "Ammon Phipps",
            "label": "My Label",
            "description": "My Description",
            "color": "red",
            "size": "large",
        }
        assert "otherAttributes" not in item


def testDynamoUpdateChangesStoredItem():
    # Tests that update changes, removes, and adds attributes on the stored item
    with mock_aws():
        table, store = makeDynamoStore()
        store.create(makeWidget())

        store.update(makeRequest("update", label="New Label", description="",
                                 otherAttributes=[OtherAttribute("color", "blue"), OtherAttribute("size", ""), OtherAttribute("weight", "heavy")]))

        item = table.get_item(Key={"id": "widget-1"})["Item"]
        assert item == {
            "id": "widget-1",
            "owner": "Ammon Phipps",
            "label": "New Label",
            "color": "blue",
            "weight": "heavy",
        }


def testDynamoUpdateMissingWidgetWarns(caplog):
    # Tests that updating a widget that doesn't exist logs a warning and doesn't create it
    with mock_aws():
        table, store = makeDynamoStore()

        store.update(makeRequest("update", label="New Label"))

        assert "Update failed" in caplog.text
        assert "Item" not in table.get_item(Key={"id": "widget-1"})


def testDynamoDeleteRemovesItem():
    # Tests that delete removes the stored item
    with mock_aws():
        table, store = makeDynamoStore()
        store.create(makeWidget())

        store.delete(makeRequest("delete"))

        assert "Item" not in table.get_item(Key={"id": "widget-1"})


def testDynamoDeleteMissingWidgetWarns(caplog):
    # Tests that deleting a widget that doesn't exist logs a warning instead of raising
    with mock_aws():
        table, store = makeDynamoStore()

        store.delete(makeRequest("delete"))

        assert "Delete failed" in caplog.text

