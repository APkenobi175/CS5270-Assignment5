# Consumer program: reads widget requests one at a time and stores the widgets

import argparse
import logging
import time

import boto3

from models import ParserException, WidgetFactory, WidgetRequestFactory
from requestSources import S3RequestSourceStrategy
from widgetStores import DynamoDBWidgetStoreStrategy, S3WidgetStoreStrategy

logger = logging.getLogger(__name__)


def parseArgs(argv=None):
    # Read the command-line arguments for the storage strategy and resources to use. Uses argparse so that its easy to parse arguments
    parser = argparse.ArgumentParser(description="Consumes widget requests and stores the widgets")
    parser.add_argument("--storage", choices=["s3", "dynamodb"], required=True, help="where to store widgets")
    parser.add_argument("--request-bucket", required=True, help="S3 bucket to read widget requests from (Bucket 2)")
    parser.add_argument("--widget-bucket", help="S3 bucket to store widgets in (Bucket 3), needed for --storage s3")
    parser.add_argument("--table", default="widgets", help="DynamoDB table to store widgets in, used for --storage dynamodb")
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


def createStore(args):
    # Pick the widget store strategy based on the --storage argument
    if args.storage == "s3":
        return S3WidgetStoreStrategy(boto3.client("s3"), args.widget_bucket)
    return DynamoDBWidgetStoreStrategy(boto3.resource("dynamodb").Table(args.table))


def processRequest(text, store):
    # Parse a request and send it to the storage, log a bad request if it fails
    try:
        request = WidgetRequestFactory().fromJson(text)
    except Exception as e:
        logger.warning("Error: Bad Request: " + str(e))
        return

    if request.requestType == "create":
        store.create(WidgetFactory().fromRequest(request))
    else:
        logger.warning(request.requestType + " requests not supported until assignment 7, skipping " + request.requestId)


def main():

    # 1. Parse the command line arguments
    args = parseArgs()
    # 2. Set up logging to file and console
    setupLogging(args.log_file)

    # 3. Create the request source and widget store
    source = S3RequestSourceStrategy(boto3.client("s3"), args.request_bucket)
    store = createStore(args)
    logger.info("Consumer Started: reading from " + str(args.request_bucket) + ", storing in " + str(args.storage))

    # Loop until user cancels
    try:
        while True:
            text = source.getNextRequest()
            if text is not None:
                try:
                    processRequest(text, store)
                except Exception as e:
                    logger.error("Failed to process request: " + str(e))
            
            else:
                # No request available, sleep for a bit
                time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("Consumer stopped")


# Only run the consumer when started directly (python main.py), not when imported by tests
if __name__ == "__main__":
    main()
