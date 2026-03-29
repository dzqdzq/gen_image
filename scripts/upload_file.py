import os
import time
from os.path import basename

import tos

from config import TOS_BUCKET, TOS_ENDPOINT, TOS_REGION

_client = None

def _get_client():
    global _client
    if _client is None:
        ak = os.getenv("TOS_ACCESS_KEY")
        sk = os.getenv("TOS_SECRET_KEY")
        if not ak or not sk:
            return None
        _client = tos.TosClientV2(ak, sk, TOS_ENDPOINT, TOS_REGION)
    return _client


def get_https_url(object_key):
    return f"https://{TOS_BUCKET}.{TOS_ENDPOINT}/{object_key}"


def upload_file(file_name):
    client = _get_client()
    if client is None:
        print(
            "错误：未设置 TOS 凭证。请先 export TOS_ACCESS_KEY 与 TOS_SECRET_KEY。"
        )
        return None
    try:
        if not os.path.exists(file_name):
            print(f"ERROR: File {file_name} does not exist")
            return None
        object_key = f"{int(time.time() * 1000)}_{basename(file_name)}"
        client.put_object_from_file(TOS_BUCKET, object_key, file_name)
        url = get_https_url(object_key)
        print(f"{file_name} 远程访问URL地址为: {url}")
        return url
    except tos.exceptions.TosClientError as e:
        print("fail with client error, message:{}, cause: {}".format(e.message, e.cause))
    except tos.exceptions.TosServerError as e:
        print("fail with server error, code: {}".format(e.code))
        print("error with request id: {}".format(e.request_id))
        print("error with message: {}".format(e.message))
        print("error with http code: {}".format(e.status_code))
        print("error with ec: {}".format(e.ec))
        print("error with request url: {}".format(e.request_url))
    except Exception as e:
        print("fail with unknown error: {}".format(e))
    return None

if __name__ == "__main__":
    upload_file("/Users/xmac/Downloads/25337000000281731754.png")
