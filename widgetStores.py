
# Adds widgets to AWS, uses different classes based on the storage mechanism
# This uses the strategy pattern :) (from CS5700: object oriented programming)


import logging

from botocore.exceptions import ClientError

from models import OtherAttribute, Widget, WidgetFactory

logger = logging.getLogger(__name__)


class WidgetStoreInterface:
    # Base class for widget store strategies (would be an interface in java/kotlin/c#)
    def __init__(self):
        pass

    def create(self, widget):
        raise NotImplementedError

    def update(self, request):
        
        raise NotImplementedError

    def delete(self, request):
        raise NotImplementedError


class S3WidgetStoreStrategy(WidgetStoreInterface):
    # Strategy for storing widgets in S3

    def __init__(self, s3Client, bucketName):
        self.s3Client = s3Client
        self.bucketName = bucketName

    def create(self, widget):
        # Save the widget as a JSON string at widgets/{owner}/{widgetId}
        key = self._widgetKey(widget)
        self.s3Client.put_object(Bucket=self.bucketName, Key=key, Body=widget.toJson())
        logger.info("Created widget " + str(widget.widgetId) + " in S3 bucket " + self.bucketName + " at " + key)

    def update(self, request):
        # 1. read the existing widget, warn and stop if it's not there
        key = self._widgetKey(request)
        widget = self._readWidget(key)
        if widget is None:
            logger.warning("Update failed: widget " + request.widgetId + " not found in S3 bucket " + self.bucketName + " at " + key)
            return

        # 2. change it and write it back
        widget.applyUpdate(request)
        self.s3Client.put_object(Bucket=self.bucketName, Key=key, Body=widget.toJson())
        logger.info("Updated widget " + request.widgetId + " in S3 bucket " + self.bucketName + " at " + key)

    def delete(self, request):
        # Check if the widge exists, stop if it dont
        key = self._widgetKey(request)
        if not self._exists(key):
            logger.warning("Delete failed: widget " + request.widgetId + " not found in S3 bucket " + self.bucketName + " at " + key)
            return

        self.s3Client.delete_object(Bucket=self.bucketName, Key=key)
        logger.info("Deleted widget " + request.widgetId + " from S3 bucket " + self.bucketName + " at " + key)

    def _readWidget(self, key):
        # return the widget stored at key, or None if there isn't one
        try:
            obj = self.s3Client.get_object(Bucket=self.bucketName, Key=key)
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return None
            raise
        return WidgetFactory().fromJson(obj["Body"].read().decode("utf-8"))

    def _exists(self, key):
        # returns if the object at a key rexists or not
        try:
            self.s3Client.head_object(Bucket=self.bucketName, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return False
            raise

    def _widgetKey(self, widget):
        # Build the S3 key for a widget 
        return "widgets/" + self._ownerKey(widget.owner) + "/" + widget.widgetId

    def _ownerKey(self, owner):
        # Turn an owner name into its key form, replacing spaces with dashes and all lower case
        return owner.replace(" ", "-").lower()


class DynamoDBWidgetStoreStrategy(WidgetStoreInterface):
    # Strategy for storing widgets in DynamoDB

    def __init__(self, table):
        self.table = table

    def create(self, widget):
        
        # Save the widget as a DynamoDB item
        self.table.put_item(Item=self._toItem(widget))
        logger.info("Created widget " + str(widget.widgetId) + " in DynamoDB table " + self.table.name)

    def update(self, request):
        # 1. read the existing widget, warn and stop if it's not there
        response = self.table.get_item(Key={"id": request.widgetId})
        if "Item" not in response:
            logger.warning("Update failed: widget " + request.widgetId + " not found in DynamoDB table " + self.table.name)
            return

        # 2. change it and write the whole item back
        widget = self._fromItem(response["Item"])
        widget.applyUpdate(request)
        self.table.put_item(Item=self._toItem(widget))
        logger.info("Updated widget " + request.widgetId + " in DynamoDB table " + self.table.name)

    def delete(self, request):
        # ALL_OLD returns the deleted item, so no Attributes means it wasn't there
        response = self.table.delete_item(Key={"id": request.widgetId}, ReturnValues="ALL_OLD")
        if "Attributes" not in response:
            logger.warning("Delete failed: widget " + request.widgetId + " not found in DynamoDB table " + self.table.name)
            return
        logger.info("Deleted widget " + request.widgetId + " from DynamoDB table " + self.table.name)

    def _fromItem(self, item):
        # Build a Widget from a DynamoDB item (the reverse of _toItem)
        otherAttributes = []
        for name, value in item.items():
            if name not in ("id", "owner", "label", "description"):
                otherAttributes.append(OtherAttribute(name, value))

        return Widget(item["id"], item["owner"], item.get("label"), item.get("description"), otherAttributes)

    def _toItem(self, widget):
        # Build a DynamoDB item where every other attribute is its own top-level attribute
        item = {"id": widget.widgetId, "owner": widget.owner}

        if widget.label is not None:
            item["label"] = widget.label
        if widget.description is not None:
            item["description"] = widget.description

        for attr in widget.otherAttributes:
            item[attr.name] = attr.value

        return item
