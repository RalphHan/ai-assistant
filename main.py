import json
import os

import dotenv

dotenv.load_dotenv()

import random
from http import HTTPStatus
from dashscope import AioGeneration
from send_sms import send_sms
import asyncio
import re
from user_config import USERS

model = "qwen-turbo"

pattern1 = re.compile(r'[a-zA-Z ]')

replacements = {
    '，': ',', '。': '.', '：': ':', '；': ';',
    '？': '?', '！': '!', '“': '"', '”': '"',
    '‘': "'", '’': "'", '（': '(', '）': ')',
    '【': '[', '】': ']', '—': '-', '…': '...'
}
pattern2 = re.compile('|'.join(re.escape(key) for key in replacements.keys()))

pattern3 = re.compile(r'[^\u4e00-\u9fff\d\n,\.!?;:"\'()—\[\]\-]+')


async def call_model(messages, enable_search=True):
    for i in range(3):
        try:
            response = await AioGeneration.call(model=model,
                                                messages=messages,
                                                seed=random.randint(1, 10000),
                                                result_format='message',
                                                enable_search=enable_search)
            if response.status_code != HTTPStatus.OK:
                print('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                    response.request_id, response.status_code,
                    response.code, response.message
                ))
            assert response.status_code == HTTPStatus.OK
            assistant_output = response.output.choices[0].message
            message = assistant_output.content
            message = pattern1.sub('', message)
            message = pattern2.sub(lambda m: replacements[m.group(0)], message)
            message = pattern3.sub('', message)
            return message
        except Exception:
            import traceback
            traceback.print_exc()
    return "无数据"


async def get_holiday():
    messages = [{'role': 'system', 'content': '你是一个日历查询机器人'},
                {'role': 'user', 'content': '今天是工作日还是某个节假日？总结为不超过5字'}]
    return (await call_model(messages))[:30]


async def get_weather(city):
    messages = [{'role': 'system', 'content': '你是一个天气查询机器人'},
                {'role': 'user', 'content': f'今天{city}天气怎么样？总结为不超过25字'}]
    return (await call_model(messages))[:30]


pattern4 = re.compile(r'^\d+[.,]?')


async def get_hashtags():
    messages = [{'role': 'system', 'content': '你是一个新闻推送机器人'},
                {'role': 'user', 'content': '今天有何头条新闻？'}]
    response1 = await call_model(messages)
    messages.append({'role': 'assistant', 'content': response1})
    messages.append({'role': 'user', 'content': '总结成三句话，每句一行，每句不超过25字'})
    response2 = await call_model(messages, enable_search=False)
    hashtags = []
    cnt = 0
    for line in response2.strip().splitlines():
        line = pattern4.sub('', line).strip()[:30]
        if line:
            hashtags.append(line)
            cnt += 1
            if cnt >= 3:
                break
    for i in range(cnt, 3):
        hashtags.append("无数据")
    return hashtags


async def get_blessings(holiday, desc, city, weather, hashtags):
    hashtag_message = '；'.join(hashtags)
    prompt = f"{holiday}\n我是一名{desc}，我在{city}，今天的天气是：{weather}，\n今天的新闻是：{hashtag_message}\n请依照这些信息，为我写一段晨间祝福语。总结为不超过25字"
    print(prompt)
    messages = [{'role': 'system', 'content': '你是一生成祝福语的机器人'},
                {'role': 'user',
                 'content': prompt}]
    return (await call_model(messages, enable_search=False))[:30]


async def generate_messages(user_name):
    try:
        user = USERS[user_name]
        city = user['city']
        if isinstance(city, list):
            import datetime
            today = datetime.date.today()
            weekday_index = today.weekday()
            city = city[weekday_index]
        desc = user['desc']
        number = os.environ[f'NUMBER_{user_name.upper()}']
        holiday, weather, hashtags = await asyncio.gather(get_holiday(), get_weather(city), get_hashtags())
        blessings = await get_blessings(holiday, desc, city, weather, hashtags)
        message = {
            "phone_numbers": number,
            "name": user_name,
            "city": city,
            "weather": weather,
            "hashtag1": hashtags[0],
            "hashtag2": hashtags[1],
            "hashtag3": hashtags[2],
            "blessings": blessings,
        }
        return message
    except Exception:
        import traceback
        traceback.print_exc()
        return {"name": user_name}


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-sms', action='store_true', help='Do not send SMS, generate message only')
    parser.add_argument('--to', type=str, default='all', help='User to send SMS to, default to all, separated by comma')
    args = parser.parse_args()
    if args.to == 'all':
        args.to = list(USERS.keys())
    else:
        args.to = args.to.strip().split(',')
    messages = await asyncio.gather(*[generate_messages(user_name) for user_name in args.to])
    print(json.dumps(messages, indent=2, ensure_ascii=False))
    if not args.no_sms:
        state = await asyncio.gather(*[send_sms(**message) for message in messages])
        print(args.to)
        print(state)


if __name__ == '__main__':
    asyncio.run(main())
