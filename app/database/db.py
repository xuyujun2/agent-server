import pymysql
from dbutils.pooled_db import PooledDB

from app.config import Config


pool = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=2,
    maxcached=5,
    blocking=True,
    host=Config.DB_HOST,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    database=Config.DB_NAME,
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True,
)


def get_db_connection():
    """从连接池获取数据库连接。"""
    return pool.connection()

def execute_query(sql, params=None):
    """执行查询，返回结果列表"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        return cursor.fetchall()
    finally:
        conn.close()

def execute_update(sql, params=None):
    """执行更新/插入，返回影响行数"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        rows = cursor.execute(sql, params or ())
        conn.commit()
        return rows
    finally:
        conn.close()
