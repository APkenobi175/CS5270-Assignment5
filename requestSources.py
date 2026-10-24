# Gets widget requests from wherever they are stored, one at a time
# I'll use the strategy pattern here too (from CS5700: object oriented programming)

import logging

logger = logging.getLogger(__name__)


class RequestSourceInterface:
    # Base class for request source strategies
    def __init__(self):
        pass

    def getNextRequest(self):
        raise NotImplementedError

class S3RequestSourceStrategy(RequestSourceInterface):
    # Strategy for fetching widget requests from S3
    def __init__(self, s3Client, bucketName):
        self.s3Client = s3Client
        self.bucketName = bucketName

    def getNextRequest(self):
        # Returns the JSON text of the request with the smallest key and deletes it, or None if there are none

        # 1. list objects v2, only ask for one key
        response = self.s3Client.list_objects_v2(Bucket=self.bucketName, MaxKeys=1)
        if "Contents" not in response:
            return None
        key = response["Contents"][0]["Key"]

        # 2. read the request text
        object = self.s3Client.get_object(Bucket=self.bucketName, Key=key)
        text = object["Body"].read().decode("utf-8")

        # 3. delete the request so it is not processed again
        self.s3Client.delete_object(Bucket=self.bucketName, Key=key)
        logger.info("Got request %s from S3 bucket %s", key, self.bucketName)

        return text
