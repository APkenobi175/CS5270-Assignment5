# Unit tests for requestSources.py

import boto3
from moto import mock_aws

from requestSources import S3RequestSourceStrategy


def makeBucket():
    # Create a fake S3 client with an empty request bucket (must be called inside mock_aws)
    s3Client = boto3.client("s3", region_name="us-east-1")
    s3Client.create_bucket(Bucket="test-requests")
    return s3Client


#----------------------------
# S3RequestSourceStrategy Tests
#----------------------------

def testGetNextRequestEmptyBucketReturnsNone():
    # Tests that an empty bucket returns None
    with mock_aws():
        s3Client = makeBucket()
        source = S3RequestSourceStrategy(s3Client, "test-requests")

        assert source.getNextRequest() is None


def testGetNextRequestReturnsTextAndDeletesIt():
    # Tests that a request's text is returned and the request is removed from the bucket
    with mock_aws():
        s3Client = makeBucket()
        s3Client.put_object(Bucket="test-requests", Key="1", Body='{"type": "create"}')
        source = S3RequestSourceStrategy(s3Client, "test-requests")

        text = source.getNextRequest()

        assert text == '{"type": "create"}'
        assert "Contents" not in s3Client.list_objects_v2(Bucket="test-requests")


def testGetNextRequestReturnsSmallestKeyFirst():
    # Tests that requests come back in key order, one at a time, then None when empty
    with mock_aws():
        s3Client = makeBucket()
        s3Client.put_object(Bucket="test-requests", Key="b", Body="second")
        s3Client.put_object(Bucket="test-requests", Key="c", Body="third")
        s3Client.put_object(Bucket="test-requests", Key="a", Body="first")
        source = S3RequestSourceStrategy(s3Client, "test-requests")

        assert source.getNextRequest() == "first"
        assert source.getNextRequest() == "second"
        assert source.getNextRequest() == "third"
        assert source.getNextRequest() is None
