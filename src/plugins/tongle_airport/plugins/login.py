from nonebot import get_plugin_config, on_command, on_request, logger
from nonebot.adapters.onebot.v11.event import Event, PrivateMessageEvent, FriendRequestEvent
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata
from nonebot.params import CommandArg, ArgPlainText
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.bot import Bot
from asyncio import sleep
import datetime
import asyncio
from ..config import Config
import requests
import hashlib
import json
from .sqlite import userInfo, userEmail, setUserPwd, setUserEmail, setUserAuthData, userAuthData

__plugin_meta__ = PluginMetadata(
    name="tongle-login",
    description="登录Tongle Airport",
    usage="/login,/set-pwd,/set-email,/request-add",
    config=Config,
)

config = get_plugin_config(Config)

login = on_command(cmd="login",priority=50,block=True)
pwd = on_command(cmd="set-pwd",priority=50,block=True)
email = on_command(cmd="set-email",priority=50,block=True)
registFriendRequest = on_command(cmd="add",priority=50,block=True)

@pwd.handle()
async def handle_function(event: Event, matcher: Matcher, args: Message = CommandArg()):
    if not isinstance(event, PrivateMessageEvent):
        await pwd.finish(Message("请在私聊中使用!\n向bot发送加好友请求,bot会自动同意"))
    if args.extract_plain_text():
        matcher.set_arg("pwd",args)

@pwd.got("password","请输入密码")
async def handle_function(event: PrivateMessageEvent, matcher: Matcher, password: Message = ArgPlainText()):
    with open("src/plugins/tongle_airport/sqlTableName.txt","r") as file:
        tableName = file.readline()
    setUserPwd(tableName=tableName, qqid=event.get_user_id(), password=str(password))
    await pwd.finish(Message("设置成功!"))

@email.handle()
async def handle_function(matcher: Matcher, args: Message = CommandArg()):
    if args.extract_plain_text():
        matcher.set_arg("userEmail",args)

@email.got("userEmail","请输入邮箱地址")
async def handle_function(event: Event, userEmail: Message = ArgPlainText()):
    with open("src/plugins/tongle_airport/sqlTableName.txt","r") as file:
        tableName = file.readline()
    setUserEmail(tableName=tableName, qqid=event.get_user_id(), email=str(userEmail))
    await email.finish(Message("设置成功!"))

@login.handle()
async def _(event: Event):
    with open("src/plugins/tongle_airport/sqlTableName.txt","r") as file:
        tableName = file.readline()
    url = config.tongle_airport_url + "/api/v1/passport/auth/login"
    sqlData = userInfo(tableName=tableName,qqid=event.get_user_id())
    logger.debug("[SQLdata] "+str(sqlData))
    
    if not sqlData["email"]:
        await login.finish(Message("登录失败:您未记录邮箱!\n请使用/set-email记录邮箱"))
    if not sqlData["password"]:
        await login.finish(Message("登录失败:您未记录密码!\n请在私聊中使用/set-pwd记录密码"))
    
    req = {
        "email": sqlData["email"],
        "password": sqlData["password"]
    }
    resp = requests.post(url=url, data=req)
    
    if resp.ok:
        resp_data = json.loads(resp.text)
        logger.debug("[resp_data] "+str(resp_data))
        token = resp_data["data"]["token"]
        userTokenSha256 = hashlib.sha256(token.encode('utf-8')).hexdigest()
        setUserAuthData(
            tableName=tableName, 
            qqid=event.get_user_id(),
            auth_data=resp_data["data"]["auth_data"]
        )
        
        if resp_data["data"]["is_admin"]:
            await login.send(Message("尊敬的管理员,您好!"))
        await login.finish(Message(f"登录成功!\n您的token sha256为:{userTokenSha256}"))
    
    elif resp.status_code == 403:
        await login.finish(Message("登录失败!原因:邮箱或密码错误"))
    else:
        resp_data = json.loads(resp.text)
        await login.finish(Message("登录失败!原因:" + resp_data["message"]))

registedUserIds = set()

@registFriendRequest.handle()
async def _(event: Event, bot:Bot):
    await registFriendRequest.send(Message("正在处理..."))
    registedUserIds.add(event.get_user_id())
    await registFriendRequest.finish(Message(f"[CQ:at,qq={event.get_user_id()}]您申请的加好友请求已经被注册\n请在10分钟内向bot发送申请"))

acceptFriendRequest = on_request(priority=50,block=True)

@acceptFriendRequest.handle()
async def _(event: FriendRequestEvent, bot: Bot):
    if event.get_user_id() not in registedUserIds:
        await acceptFriendRequest.reject()
    
    await bot.set_friend_add_request(flag=event.flag,approve=True)
    registedUserIds.remove(event.get_user_id())
    await asyncio.sleep(3)
    await acceptFriendRequest.finish(Message("已同意您的好友请求"))

getInfo = on_command(cmd="info",priority=50,block=True)

@getInfo.handle()
async def _(event: Event):
    with open("src/plugins/tongle_airport/sqlTableName.txt","r") as file:
        tableName = file.readline()
    url = config.tongle_airport_url + "/api/v1/user/info"
    if not userAuthData(tableName=tableName,qqid=event.get_user_id()):
        await getInfo.finish(Message("获取用户信息失败!原因:未登录"))
    headers = {
        "Authorization": userAuthData(tableName=tableName,qqid=event.get_user_id())
    }
    resp1 = requests.get(url=url, headers=headers)
    url = config.tongle_airport_url + "/api/v1/user/getSubscribe"
    resp2 = requests.get(url=url, headers=headers)
    if resp1.status_code == 200 and resp2.status_code == 200:
        logger.debug("[resp1] "+str(resp1.text))
        logger.debug("[resp2] "+str(resp2.text))
        resp1_data = json.loads(resp1.text)
        resp2_data = json.loads(resp2.text)
        info = "邮箱:" + resp1_data["data"]["email"] + "\n"
        transfer_enable = resp1_data["data"]["transfer_enable"]
        info += "总流量:" + str(transfer_enable / 1024 / 1024 / 1024) + "GB\n"
        transfer_used = resp2_data["data"]["u"] + resp2_data["data"]["d"]
        transfer_used_GB = round(transfer_used / 1024 / 1024 / 1024, 3)
        info += "已使用流量:" + str(transfer_used_GB) + "GB\n"
        if resp1_data["data"]["banned"]:
            banned_text = "是"
        else:
            banned_text = "否"
        info += "封禁状态:" + banned_text + "\n"
        balance = str(resp1_data["data"]["balance"])
        formatted_balance = balance[:-2] + "." + balance[-2:]
        info += "账户余额:" + formatted_balance
        await getInfo.finish(Message(f"用户信息:\n{info}"))
    elif resp1.status_code == 403 or resp2.status_code == 403:
        await getInfo.finish(Message("获取用户信息失败!原因:登录过期,请重新登录"))
    else:
        await getInfo.finish(Message("获取用户信息失败!原因:未知错误"))