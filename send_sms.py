import json
import os

from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysmsapi_20170525_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient


def create_client() -> Dysmsapi20170525Client:
    config = open_api_models.Config(
        access_key_id=os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'],
        access_key_secret=os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET']
    )
    config.endpoint = 'dysmsapi.aliyuncs.com'
    return Dysmsapi20170525Client(config)


client = create_client()


async def send_sms(phone_numbers=None, **kwargs):
    if not phone_numbers:
        return False
    send_sms_request = dysmsapi_20170525_models.SendSmsRequest(
        phone_numbers=phone_numbers,
        sign_name=os.environ['SIGN_NAME'],
        template_code=os.environ['TEMPLATE_CODE'],
        template_param=json.dumps(kwargs),
    )
    try:
        await client.send_sms_with_options_async(send_sms_request, util_models.RuntimeOptions())
        return True
    except Exception as error:
        print(error.message)
        print(error.data.get("Recommend"))
        UtilClient.assert_as_string(error.message)
    return False
