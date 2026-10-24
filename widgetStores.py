
# Adds widgets to AWS, uses different classes based on the storage mechanism
# This uses the strategy pattern :) (from CS5700: object oriented programming)


import logging

logger = logging.getLogger(__name__)


class WidgetStoreInterface:
    # Base class for widget store strategies (would be an interface in java/kotlin/c#)
    def __init__(self):
        pass

    def create(self, widget):
        raise NotImplementedError

    def update(self, widget):
        print("Hello world, this won't do nothin until assignment 7")
        raise NotImplementedError

    def delete(self, widget):
        print("Hello world, this won't do nothin until assignment 7")
        raise NotImplementedError


class S3WidgetStoreStrategy(WidgetStoreInterface):
    # Strategy for storing widgets in S3

    def __init__(self, s3Client, bucketName):
        self.s3Client = s3Client
        self.bucketName = bucketName

    def create(self, widget):
        # Save the widget as a JSON string at widgets/{owner}/{widgetId}
        key = self.widgetKey(widget)
        self.s3Client.put_object(Bucket=self.bucketName, Key=key, Body=widget.toJson())
        logger.info("Created widget %s in S3 bucket %s at %s", widget.widgetId, self.bucketName, key)

    def widgetKey(self, widget):
        # Build the S3 key for a widget
        return "widgets/" + self.ownerKey(widget.owner) + "/" + widget.widgetId

    def ownerKey(self, owner):
        # Turn an owner name into its key form, replacing spaces with dashes and all lower case
        return owner.replace(" ", "-").lower()


class DynamoDBWidgetStoreStrategy(WidgetStoreInterface):
    # Strategy for storing widgets in DynamoDB

    def __init__(self, table):
        self.table = table

    def create(self, widget):
        # Save the widget as a DynamoDB item
        self.table.put_item(Item=self.toItem(widget))
        logger.info("Created widget %s in DynamoDB table %s", widget.widgetId, self.table.name)

    def toItem(self, widget):
        # Build a DynamoDB item where every other attribute is its own top-level attribute
        item = {"id": widget.widgetId, "owner": widget.owner}

        if widget.label is not None:
            item["label"] = widget.label
        if widget.description is not None:
            item["description"] = widget.description

        for attr in widget.otherAttributes:
            item[attr.name] = attr.value

        return item
