# CS5270 HW6

Reads widget requests one at a time from an S3 bucket and stores the widgets in either another S3 bucket or a DynamoDB table.

## Setup

Requires Python 3 and AWS credentials set up for the AWS CLI 

To install all dependancies for this project run this in your terminal:

```
pip install -r requirements.txt
```

## How to run

Store widgets in S3:

```
python main.py --storage s3 --request-bucket <request-bucket> --widget-bucket <widget-bucket>
```

Store widgets in DynamoDB:

```
python main.py --storage dynamodb --request-bucket <request-bucket> --table widgets
```

The consumer runs until you press Ctrl+C. Run `python main.py --help` to see all options.

Here are a list of all the args available to run with the program:

| arg          | Description                                            |
|--------------------|--------------------------------------------------------|
| `--storage`        | `s3` or `dynamodb`                                     |
| `--request-bucket` | Bucket to read widget requests from                    |
| `--widget-bucket`  | Bucket to store widgets in (required for `s3`)         |
| `--table`          | DynamoDB table to store widgets in (default `widgets`) |
| `--log-file`       | the Log file to write to (default is `consumer.log`)   |


Arguments are managed by python's argparse module.

## Unit Tests

For this assignment I used pytest as a framework for my unit tests

To run the unit tests run this command:

```
python -m pytest -v
```

The tests use the `moto` library to fake AWS services, that way I can test on local hardware without needing aws credentials to run the unit tests.


## Credits

The request sources and widget stores use the Strategy design pattern, and factory pattern learned in CS5700.


