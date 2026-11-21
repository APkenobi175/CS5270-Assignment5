# Consumer program: reads widget requests one at a time and stores the widgets

import argparse
import logging
import time

import boto3

from models import WidgetFactory, WidgetRequestFactory
from requestSources import S3RequestSourceStrategy, SQSRequestSourceStrategy
from widgetStores import DynamoDBWidgetStoreStrategy, S3WidgetStoreStrategy

logger = logging.getLogger(__name__)


def parseArgs(argv=None):
    # Read the command-line arguments for the storage strategy and resources to use. Uses argparse so that its easy to parse arguments
    parser = argparse.ArgumentParser(description="Consumes widget requests and stores the widgets")
    parser.add_argument("--storage", choices=["s3", "dynamodb"], required=True, help="where to store widgets")

    # Requests come from exactly one place, either an S3 bucket or an SQS queue
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--request-bucket", help="S3 bucket to read widget requests from (Bucket 2)")
    source.add_argument("--request-queue", help="name of the SQS queue to read widget requests from")

    parser.add_argument("--widget-bucket", help="S3 bucket to store widgets in (Bucket 3), needed for --storage s3")
    parser.add_argument("--table", default="widgets", help="DynamoDB table to store widgets in, used for --storage dynamodb")
    parser.add_argument("--region", default="us-east-1", help="AWS region of the resources")
    parser.add_argument("--log-file", default="consumer.log", help="file to write the log to")

    args = parser.parse_args(argv)
    if args.storage == "s3" and args.widget_bucket is None:
        parser.error("--widget-bucket is required when --storage is s3")
    return args


def setupLogging(logFile):
    # Log to both a file and the console
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(logFile), logging.StreamHandler()],
    )


def createSource(args):
    # Pick the request source strategy based on --request-queue or --request-bucket
    if args.request_queue is not None:
        return SQSRequestSourceStrategy(boto3.client("sqs", region_name=args.region), args.request_queue)
    return S3RequestSourceStrategy(boto3.client("s3", region_name=args.region), args.request_bucket)


def createStore(args):
    # Pick the widget store strategy based on the --storage argument
    if args.storage == "s3":
        return S3WidgetStoreStrategy(boto3.client("s3", region_name=args.region), args.widget_bucket)
    return DynamoDBWidgetStoreStrategy(boto3.resource("dynamodb", region_name=args.region).Table(args.table))


def processRequest(text, store):
    # Parse a request and send it to the right store method, log a bad request if it fails
    try:
        request = WidgetRequestFactory().fromJson(text)
    except Exception as e:
        logger.warning("Error: Bad Request: " + str(e))
        return

    logger.info("Processing " + request.requestType + " request " + request.requestId + " for widget " + request.widgetId)
    if request.requestType == "create":
        store.create(WidgetFactory().fromRequest(request))
    elif request.requestType == "update":
        store.update(request)
    elif request.requestType == "delete":
        store.delete(request)


def processNextRequest(source, store):
    # Get one request and process it. Returns False if there was no request available
    text = source.getNextRequest()
    if text is None:
        return False

    try:
        processRequest(text, store)
    except Exception as e:
        # Leave the request alone so it can be tried again 
        logger.error("Failed to process request: " + str(e))
        return True

    # Done with it, so remove it from the source
    source.finishRequest()
    return True


def main():

    # 1. Parse the command line arguments
    args = parseArgs()
    # 2. Set up logging to file and console
    setupLogging(args.log_file)

    # 3. Create the request source and widget store
    source = createSource(args)
    store = createStore(args)
    sourceName = args.request_queue if args.request_queue is not None else args.request_bucket
    logger.info("Consumer Started: reading from " + sourceName + ", storing in " + args.storage)

    # Loop until user cancels
    try:
        while True:
            if not processNextRequest(source, store):
                # No request available, sleep for a bit
                time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("Consumer stopped")


# Only run the consumer when started directly (python main.py), not when imported by tests
if __name__ == "__main__":
    main()
