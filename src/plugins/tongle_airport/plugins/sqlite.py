from nonebot import get_plugin_config, get_driver
from nonebot.plugin import on_command
from nonebot.params import CommandArg, ArgPlainText
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.message import Message
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import Event, GroupMessageEvent
from nonebot.permission import SUPERUSER
import sqlite3
import re

from ..config import Config

__plugin_meta__ = PluginMetadata(
    name="tongle-sqlite",
    description="sqlite支持",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

driver = get_driver()
sqlTableSet = on_command("settable",priority=50)

@driver.on_startup
async def _():
    global conn
    global curs
    conn = sqlite3.Connection("src/plugins/tongle_airport/botUser.db")
    curs = conn.cursor()

@driver.on_shutdown
async def _():
    curs.close
    conn.close

@sqlTableSet.handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    if args.extract_plain_text():
        matcher.set_arg("tableName", args)

@sqlTableSet.got("tableName","请发送表名")
async def _(tableName: str = ArgPlainText()):
    await sqlTableSet.send(Message("开始创建......"))
    
    if not re.match("^[a-zA-Z]+[a-zA-Z0-9_]*$",tableName):
        await sqlTableSet.finish(Message("不正确的表名!\n格式如以下正则表达式:\n^[a-zA-Z_]+[0-9]*$"))
    
    try:
        curs.execute(f"""
                CREATE TABLE {tableName}(
                    qqid    text    NOT NULL    PRIMARY KEY,
                    email   text,
                    pwd     text,
                    auth_data  text
                );
        """)
    except Exception as err:
        await sqlTableSet.finish(Message(f"创建表{tableName}失败!\n错误:{err}"))
    with open("./src/plugins/tongle_airport/sqlTableName.txt","w+") as file:
        file.write(tableName)
    conn.commit()
    await sqlTableSet.finish(Message(f"成功创建表{tableName}!"))

def userEmail(tableName, qqid) -> str|None:
    """返回qq号所对应用户的邮箱地址"""
    curs.execute(f"""
        SELECT email 
        FROM {tableName}
        WHERE qqid=?""", (qqid,))
    result = curs.fetchone()
    return result[0] if result else None

def userPwd(tableName, qqid) -> str|None:
    """返回qq号所对应用户的密码"""
    curs.execute(f"""
        SELECT pwd
        FROM {tableName}
        WHERE qqid=?""",(qqid,))
    result = curs.fetchone()
    return result[0] if result else None

def userAuthData(tableName, qqid) -> str|None:
    """返回qq号所对应用户的auth_data"""
    curs.execute(f"""
        SELECT auth_data
        FROM {tableName}
        WHERE qqid=?""",(qqid,))
    result = curs.fetchone()
    return result[0] if result else None

def userInfo(tableName, qqid) -> dict:
    """userEmail+userPwd+userAuthData"""
    userInfo = {
        "qqid": qqid,
        "email": userEmail(tableName=tableName,qqid=qqid),
        "password": userPwd(tableName=tableName,qqid=qqid),
        "auth_data": userAuthData(tableName=tableName,qqid=qqid)
    }
    return userInfo

def setUserEmail(tableName, qqid, email):
    """设置qq号所对应用户的邮箱地址"""
    curs.execute(f"""
    SELECT count(*)
    FROM {tableName}
    WHERE qqid=?;""",(qqid,))
    if curs.fetchone()[0] == 0:
        curs.execute(f"""
        INSERT INTO {tableName}(qqid,email)
        VALUES(?,?);""",(qqid,email))
    else:
        curs.execute(f"""
        UPDATE {tableName}
        SET email=?
        WHERE qqid=?;""",(email,qqid))
    conn.commit()

def setUserPwd(tableName, qqid, password):
    """设置qq号所对应用户的密码"""
    curs.execute(f"""
    SELECT count(*)
    FROM {tableName}
    WHERE qqid=?;""",(qqid,))
    if curs.fetchone()[0] == 0:
        curs.execute(f"""
        INSERT INTO {tableName}(qqid,pwd)
        VALUES(?,?);""",(qqid,password))
    else:
        curs.execute(f"""
        UPDATE {tableName}
        SET pwd=?
        WHERE qqid=?;""",(password,qqid))
    conn.commit()
    
def setUserAuthData(tableName, qqid, auth_data):
    """设置qq号所对应用户的auth_data"""
    curs.execute(f"""
    UPDATE {tableName}
    SET auth_data=?
    WHERE qqid=?;""",(auth_data,qqid))
    conn.commit()