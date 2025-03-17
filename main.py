from astrbot.api.star import register, Star, Context
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
import astrbot.api.message_components as mc
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from astrbot.api import logger
import json
import requests

# 假设有一个地方存储用户的定时任务设置
data_path = "data/plugins/astrbot_plugin_yiyan/scheduled_greetings.json"

@register("morning_greeting", "AuthorName", "设置定时任务在指定时间发送问候语", "1.0.0", "https://github.com/your-repo/morning_greeting")
class MorningGreetingPlugin(Star):
    def __init__(self, context: Context, config: dict = None):  # 提供config参数的默认值
        super().__init__(context)
        self.scheduler = AsyncIOScheduler()  # 确保scheduler被初始化
        self.load_schedules()  # 加载已保存的定时任务
        self.scheduler.start()

    def load_schedules(self):
        """加载所有用户的定时任务"""
        try:
            with open(data_path, 'r') as f:
                content = f.read()  # 先读取文件内容
                if not content:  # 如果文件内容为空
                    schedules = {}  # 设置为空字典
                else:
                    schedules = json.loads(content)  # 解析 JSON 内容

                if not isinstance(schedules, dict):  # 确保数据是字典类型
                    logger.warning("警告：预期的数据格式是字典，但获取了其他类型")
                    schedules = {}

                for user_id, set_time in schedules.items():
                    self.set_schedule(user_id, set_time)
        except FileNotFoundError:
            # 如果文件不存在，则不执行任何操作或者初始化一个空文件
            schedules = {}  # 初始化为空字典
            with open(data_path, 'w') as f:
                json.dump(schedules, f)  # 创建一个空的 JSON 文件
        except json.JSONDecodeError:
            logger.error("错误：无法解码JSON文件的内容")

    def save_schedule(self, user_id, set_time):
        """保存用户的定时任务设置"""
        try:
            with open(data_path, 'r') as f:
                content = f.read()
                if not content:  # 如果文件为空
                    schedules = {}
                else:
                    schedules = json.loads(content)
        except FileNotFoundError:
            logger.error("找不到文件：{}".format(data_path))
            schedules = {}  # 如果文件不存在，则初始化为空字典
        except json.JSONDecodeError as e:
            logger.error("JSON解码错误：{}".format(e))
            schedules = {}  # 如果文件内容不是有效的JSON，则初始化为空字典

        # 确保数据是一个字典
        if not isinstance(schedules, dict):
            logger.warning("预期的数据格式是字典，但获取了其他类型")
            schedules = {}

        schedules[user_id] = set_time
        with open(data_path, 'w') as f:
            json.dump(schedules, f, indent=4)  # 使用indent使输出更易读

    def set_schedule(self, user_id, set_time_str):
        """为用户设置定时任务"""
        try:
            hour, minute = map(int, set_time_str.split(':'))  # 解析输入的时间字符串
            self.scheduler.add_job(self.send_greeting, 'cron', args=[user_id], hour=hour, minute=minute, misfire_grace_time=60)
        except ValueError:
            logger.error("输入的时间格式不正确，请使用HH:MM格式")

    async def send_greeting(self, user_id):
        """定时任务触发时发送问候语"""
        await self.context.send_message(user_id, MessageChain(chain=[
            mc.Plain(str(self.getmsg()))
        ]))

    def getmsg(self):
        url = "https://v1.hitokoto.cn/?c=i&c=d&encode=json&charset=utf-8"
        payload = {}
        headers = {
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
            'Accept': '*/*',
            'Host': 'v1.hitokoto.cn',
            'Connection': 'keep-alive'
        }

        try:
            response = requests.request("GET", url, headers=headers, data=payload)
        except BaseException:
            logger.error("api调用异常!")
        else:
            if response.status_code == 200:
                date = response.json()
                hitokoto = date["hitokoto"]
                from_where = date['from']
                from_who = date['from_who']

                if from_where is None:
                    from_where = " "
                if from_who is None:
                    from_who = ""

                result = hitokoto + "\n" + "    ---" + from_where + " " + from_who
                return result
            else:
                logger.error("api调用异常！")
                return "err"

    @filter.command("stime")
    async def set_timer(self, event: AstrMessageEvent, timer: str):
        """设置定时任务"""
        try:
            self.set_schedule(event.unified_msg_origin, timer)
            self.save_schedule(event.unified_msg_origin, timer)
            yield event.plain_result("设置成功！将在每天{}向您发送问候。".format(timer))
        except ValueError:
            yield event.plain_result("请按照HH:MM格式输入时间。")

    @filter.command("nihao")
    async def nihao(self, event: AstrMessageEvent):
        """立即返回一言内容"""
        yield event.plain_result(str(self.getmsg()))