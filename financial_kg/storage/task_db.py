"""SQLite任务管理"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class Task:
    """解析任务"""
    id: Optional[int] = None
    name: str = ""
    source_file: str = ""
    target_sheets: List[str] = None
    status: str = "pending"  # pending, parsing, parsed, evaluating, completed, error
    created_at: str = ""
    updated_at: str = ""
    error_msg: Optional[str] = None
    result_path: Optional[str] = None
    stats: Dict[str, Any] = None

    def __post_init__(self):
        if self.target_sheets is None:
            self.target_sheets = []
        if self.stats is None:
            self.stats = {}
        if self.created_at == "":
            self.created_at = datetime.now().isoformat()
        if self.updated_at == "":
            self.updated_at = datetime.now().isoformat()


class TaskDB:
    """SQLite任务数据库"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            from ..config import get_config
            config = get_config()
            db_path = str(config.data_dir / "tasks.db")

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source_file TEXT NOT NULL,
                target_sheets TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                updated_at TEXT,
                error_msg TEXT,
                result_path TEXT,
                stats TEXT
            )
        """)

        conn.commit()
        conn.close()

    def create_task(self, task: Task) -> int:
        """创建任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO tasks (name, source_file, target_sheets, status, created_at, updated_at, error_msg, result_path, stats)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.name,
            task.source_file,
            json.dumps(task.target_sheets),
            task.status,
            task.created_at,
            task.updated_at,
            task.error_msg,
            task.result_path,
            json.dumps(task.stats),
        ))

        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return task_id

    def get_task(self, task_id: int) -> Optional[Task]:
        """获取任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return self._row_to_task(row)

    def get_tasks(self, status: Optional[str] = None, limit: int = 100) -> List[Task]:
        """获取任务列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if status:
            cursor.execute("SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit))
        else:
            cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_task(row) for row in rows]

    def update_task(self, task_id: int, **kwargs) -> None:
        """更新任务"""
        kwargs["updated_at"] = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 构建更新SQL
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ["target_sheets", "stats"] and value is not None:
                value = json.dumps(value)
            fields.append(f"{key} = ?")
            values.append(value)

        values.append(task_id)
        sql = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"

        cursor.execute(sql, values)
        conn.commit()
        conn.close()

    def delete_task(self, task_id: int) -> None:
        """删除任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()

    def _row_to_task(self, row) -> Task:
        """数据库行转Task对象"""
        return Task(
            id=row[0],
            name=row[1],
            source_file=row[2],
            target_sheets=json.loads(row[3]) if row[3] else [],
            status=row[4],
            created_at=row[5],
            updated_at=row[6],
            error_msg=row[7],
            result_path=row[8],
            stats=json.loads(row[9]) if row[9] else {},
        )