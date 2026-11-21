# CS5270 HW7

Reads widget requests one at a time from an SQS queue or an S3 bucket and creates, updates, or deletes widgets in either another S3 bucket or a DynamoDB table.

## Setup

Requires Python 3 and AWS credentials set up for the AWS CLI 

To install all dependancies for this project run this in your terminal:

```
pip install -r requirements.txt
```

## How to run

Read requests from the SQS queue and store widgets in DynamoDB:

```
python main.py --storage dynamodb --request-queue cs5270-requests --table widgets
```

Read requests from the SQS queue and store widgets in S3:

```
python main.py --storage s3 --request-queue cs5270-requests --widget-bucket <widget-bucket>
```

Read requests from an S3 bucket instead (HW6):

```
python main.py --storage dynamodb --request-bucket <request-bucket> --table widgets
```

The consumer runs until you press Ctrl+C. Run `python main.py --help` to see all options. You can run more than one consumer on the same queue at the same time, each one gets different requests.

Here are a list of all the args available to run with the program:

| arg                | Description                                                       |
|--------------------|-------------------------------------------------------------------|
| `--storage`        | `s3` or `dynamodb`                                                |
| `--request-queue`  | Name of the SQS queue to read widget requests from                |
| `--request-bucket` | Bucket to read widget requests from                               |
| `--widget-bucket`  | Bucket to store widgets in                    |
| `--table`          | DynamoDB table to store widgets in (default `widgets`)            |
| `--region`         | AWS region of the resources (default `us-east-1`)                 |
| `--log-file`       | the Log file to write to (default is `consumer.log`)              |

Exactly one of `--request-queue` or `--request-bucket` has to be given.

Arguments are managed by python's argparse module.

## How requests are handled

- **create** makes a new widget.
- **update** changes an existing widget. Fields that are missing or null are left alone, an empty string clears the field (or removes it if it's one of the other attributes). The id and owner never change.
- **delete** removes the widget.

When reading from SQS, the consumer asks for up to 10 messages at a time using long polling and hands them out one at a time. A message is only deleted from the queue after its request is processed. If processing fails because of an AWS error, the message is left in the queue so it gets tried again after the visibility timeout.

## Unit Tests

For this assignment I used pytest as a framework for my unit tests

To run the unit tests run this command:

```
python -m pytest -v
```

The tests use the `moto` library to fake AWS services (S3, DynamoDB, and SQS), that way I can test on local hardware without needing aws credentials to run the unit tests.


## Credits

The request sources and widget stores use the Strategy design pattern, and factory pattern learned in CS5700.
