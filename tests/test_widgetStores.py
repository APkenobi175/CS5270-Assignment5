# Unit tests for widgetStores.py

import json

import boto3
from moto import mock_aws

from models import OtherAttribute, Widget
from widgetStores import DynamoDBWidgetStoreStrategy, S3WidgetStoreStrategy


def makeWidget():
    # Build a widget with every field filled in
    return Widget("widget-1", "Ammon Phipps", "My Label", "My Description", [OtherAttribute("color", "red"), OtherAttribute("size", "large")])


#----------------------------
# S3WidgetStoreStrategy Tests
#----------------------------

def testS3OwnerKeyReplacesSpacesAndLowercases():
    # Tests that owner names are lowercased and spaces become dashes
    store = S3WidgetStoreStrategy(None, "test-bucket")

    assert store.ownerKey("Ammon Taylor Phipps") == "ammon-taylor-phipps"


def testS3WidgetKey():
    # Tests that the widget key follows widgets/{owner}/{widgetId}
    store = S3WidgetStoreStrategy(None, "test-bucket")

    assert store.widgetKey(makeWidget()) == "widgets/ammon-phipps/widget-1"


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


#----------------------------
# DynamoDBWidgetStoreStrategy Tests
#----------------------------


def testDynamoToItemSkipsMissingOptionalFields():
    # Tests that a missing label and description are left out of the item
    store = DynamoDBWidgetStoreStrategy(None)

    item = store.toItem(Widget("widget-1", "Ammon Phipps"))

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

        item = table.get_item(Key={"id": "widget-1"})["Item"]
        assert item == store.toItem(makeWidget())

