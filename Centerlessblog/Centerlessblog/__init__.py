
import pymysql
from Centerlessblog.settings import BASE_DIR

# 指定了pymysql的版本：1.4.3
pymysql.version_info = (1, 4, 3, "final", 0)
pymysql.install_as_MySQLdb()  # 导入数据库配置
