import sqlite3
import pandas as pd
from pathlib import Path

class HerbDatabase:
    def __init__(self, db_path='data/herb.db'):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_db()
    
    def _ensure_db_directory(self):
        """确保数据库目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS herbs (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    effect TEXT,
                    usage TEXT
                )
            ''')
    
    def query_herbs(self, id=None, name=None, min_price=None, max_price=None):
        """查询药材数据"""
        with self._get_connection() as conn:
            query = "SELECT * FROM herbs WHERE 1=1"
            params = []
            
            if id:
                query += " AND id = ?"
                params.append(id)
            if name:
                query += " AND name LIKE ?"
                params.append(f"%{name}%")
            if min_price is not None:
                query += " AND price >= ?"
                params.append(min_price)
            if max_price is not None:
                query += " AND price <= ?"
                params.append(max_price)
            
            return pd.read_sql_query(query, conn, params=params)
    
    def save_changes(self, df):
        """保存数据修改"""
        with self._get_connection() as conn:
            # 删除所有记录
            conn.execute("DELETE FROM herbs")
            # 插入新记录
            df.to_sql('herbs', conn, if_exists='append', index=False)
    
    def export_to_csv(self, df, filename='herbs.csv'):
        """导出数据到CSV"""
        return df.to_csv(index=False)
    
    def get_all_herbs(self):
        """获取所有药材数据"""
        return self.query_herbs() 