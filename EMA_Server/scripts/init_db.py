"""Create database and tables from ORM models."""

import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.client_types import CLIENT_TYPE_WEB  # noqa: E402
from app.database import engine, get_base, get_engine  # noqa: E402
# 注册 web 模型到 WebBase.metadata（三端共用）
import app.models.web  # noqa: E402,F401

# Migration helpers use _active_engine; main() switches per client DB.
_active_engine = engine


def ensure_database() -> None:
    settings = get_settings()
    server_engine = create_engine(settings.server_url, isolation_level="AUTOCOMMIT")
    try:
        with server_engine.connect() as conn:
            for db_name in settings.all_db_names:
                conn.execute(
                    text(
                        f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                        "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                )
                print(f"Database `{db_name}` is ready.")
    finally:
        server_engine.dispose()


def ensure_session_key_column() -> None:
    with _active_engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' "
                "AND COLUMN_NAME = 'session_key'"
            )
        )
        if result.scalar() == 0:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN session_key VARCHAR(128) NULL AFTER study_status")
            )
            conn.commit()
            print("Added users.session_key column.")


def ensure_logout_at_column() -> None:
    with _active_engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_login_logs' "
                "AND COLUMN_NAME = 'logout_at'"
            )
        )
        if result.scalar() == 0:
            conn.execute(
                text(
                    "ALTER TABLE user_login_logs "
                    "ADD COLUMN logout_at DATETIME NULL COMMENT '????????????????' "
                    "AFTER logged_at"
                )
            )
            conn.commit()
            print("Added user_login_logs.logout_at column.")


def ensure_risk_session_columns() -> None:
    with _active_engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'risk_snapshots' "
                "AND COLUMN_NAME = 'task_date'"
            )
        )
        if result.scalar() == 0:
            conn.execute(
                text(
                    "ALTER TABLE risk_snapshots "
                    "ADD COLUMN task_date VARCHAR(16) NOT NULL DEFAULT '1970-01-01' "
                    "COMMENT '???? YYYY-MM-DD' AFTER user_id"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE risk_snapshots "
                    "ADD COLUMN session_id INT NOT NULL DEFAULT 1 "
                    "COMMENT '?????????? AFTER task_date"
                )
            )
            conn.execute(text("ALTER TABLE risk_snapshots DROP INDEX idx_risk_user_type"))
            conn.execute(
                text(
                    "ALTER TABLE risk_snapshots "
                    "ADD UNIQUE KEY uk_risk_snapshot (user_id, task_date, session_id, snapshot_type), "
                    "ADD KEY idx_risk_user_date (user_id, task_date)"
                )
            )
            conn.commit()
            print("Added risk_snapshots.task_date and session_id columns.")


def ensure_feedback_session_columns() -> None:
    with _active_engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'feedback_records' "
                "AND COLUMN_NAME = 'task_date'"
            )
        )
        if result.scalar() == 0:
            conn.execute(
                text(
                    "ALTER TABLE feedback_records "
                    "ADD COLUMN task_date VARCHAR(16) NOT NULL DEFAULT '1970-01-01' "
                    "COMMENT '???? YYYY-MM-DD' AFTER user_id"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE feedback_records "
                    "ADD COLUMN session_id INT NOT NULL DEFAULT 1 "
                    "COMMENT '?????????? AFTER task_date"
                )
            )
            conn.execute(text("ALTER TABLE feedback_records DROP INDEX idx_feedback_user"))
            conn.execute(
                text(
                    "ALTER TABLE feedback_records "
                    "ADD UNIQUE KEY uk_feedback_session (user_id, task_date, session_id, feedback_type), "
                    "ADD KEY idx_feedback_user_date (user_id, task_date)"
                )
            )
            conn.commit()
            print("Added feedback_records.task_date and session_id columns.")


def ensure_baseline_completed_at_column() -> None:
    with _active_engine.connect() as conn:
        has_old = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'baseline_profiles' "
                "AND COLUMN_NAME = 'completed_at_ms'"
            )
        ).scalar()
        has_new = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'baseline_profiles' "
                "AND COLUMN_NAME = 'completed_at'"
            )
        ).scalar()
        if has_old and not has_new:
            conn.execute(
                text(
                    "ALTER TABLE baseline_profiles "
                    "ADD COLUMN completed_at DATETIME NULL COMMENT '????' AFTER self_harm"
                )
            )
            conn.execute(
                text(
                    "UPDATE baseline_profiles "
                    "SET completed_at = FROM_UNIXTIME(completed_at_ms / 1000) "
                    "WHERE completed_at_ms IS NOT NULL"
                )
            )
            conn.execute(
                text(
                    "UPDATE baseline_profiles SET completed_at = CURRENT_TIMESTAMP "
                    "WHERE completed_at IS NULL"
                )
            )
            conn.execute(text("ALTER TABLE baseline_profiles DROP COLUMN completed_at_ms"))
            conn.execute(
                text(
                    "ALTER TABLE baseline_profiles "
                    "MODIFY COLUMN completed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP "
                    "COMMENT '????'"
                )
            )
            conn.commit()
            print("Migrated baseline_profiles.completed_at_ms -> completed_at.")


def ensure_ms_to_datetime_columns() -> None:
    with _active_engine.connect() as conn:
        needs = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'submissions' "
                "AND COLUMN_NAME = 'client_at_ms'"
            )
        ).scalar()
        if not needs:
            return
        sql_file = ROOT / "sql" / "15_rename_ms_to_datetime.sql"
        if not sql_file.exists():
            print("Warning: submissions.client_at_ms still exists; run sql/15_rename_ms_to_datetime.sql")
            return
        raw = sql_file.read_text(encoding="utf-8")
        for stmt in raw.split(";"):
            cleaned = "\n".join(
                line for line in stmt.splitlines() if line.strip() and not line.strip().startswith("--")
            ).strip()
            if not cleaned:
                continue
            conn.execute(text(cleaned))
        conn.commit()
        print("Migrated *_ms columns to DATETIME (15_rename_ms_to_datetime.sql).")


def ensure_users_logout_at_and_openid_index() -> None:
    with _active_engine.connect() as conn:
        has_openid = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' "
                "AND COLUMN_NAME = 'openid'"
            )
        ).scalar()
        if not has_openid:
            return

        has_logout = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' "
                "AND COLUMN_NAME = 'logout_at'"
            )
        ).scalar()
        if not has_logout:
            conn.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN logout_at DATETIME NULL COMMENT '??????? "
                    "AFTER session_key"
                )
            )
            conn.commit()
            print("Added users.logout_at column.")

        has_uk_openid = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' "
                "AND INDEX_NAME = 'uk_users_openid'"
            )
        ).scalar()
        if has_uk_openid:
            conn.execute(text("ALTER TABLE users DROP INDEX uk_users_openid"))
            conn.execute(text("ALTER TABLE users ADD KEY idx_users_openid (openid)"))
            conn.commit()
            print("Replaced users.uk_users_openid with idx_users_openid.")


def ensure_feature_session_columns() -> None:
    tables = ("text_features", "voice_features", "video_features", "behavior_features", "questions_features", "step_features")
    with _active_engine.connect() as conn:
        for table in tables:
            has_task_date = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                    f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table}' "
                    "AND COLUMN_NAME = 'task_date'"
                )
            ).scalar()
            if has_task_date:
                continue
            conn.execute(
                text(
                    f"ALTER TABLE {table} "
                    "ADD COLUMN task_date VARCHAR(16) NOT NULL DEFAULT '1970-01-01' "
                    "COMMENT '???? YYYY-MM-DD' AFTER user_id"
                )
            )
            conn.execute(
                text(
                    f"ALTER TABLE {table} "
                    "ADD COLUMN session_id INT NOT NULL DEFAULT 1 "
                    "COMMENT '?????????? AFTER task_date"
                )
            )
            conn.commit()
            print(f"Added {table}.task_date and session_id columns.")

        for table in ("text_features", "voice_features", "video_features"):
            conn.execute(
                text(
                    f"UPDATE {table} t "
                    "INNER JOIN submissions s ON t.submission_id = s.id "
                    "SET t.task_date = s.task_date, t.session_id = s.session_id"
                )
            )
        conn.commit()

        index_map = {
            "text_features": ("idx_text_feature_user", "idx_text_feature_user_date"),
            "voice_features": ("idx_voice_feature_user", "idx_voice_feature_user_date"),
            "video_features": ("idx_video_feature_user", "idx_video_feature_user_date"),
            "behavior_features": ("idx_behavior_feature_user", "idx_behavior_feature_user_date"),
        }
        for table, (old_idx, new_idx) in index_map.items():
            has_new = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.STATISTICS "
                    f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table}' "
                    f"AND INDEX_NAME = '{new_idx}'"
                )
            ).scalar()
            if has_new:
                continue
            has_old = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.STATISTICS "
                    f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table}' "
                    f"AND INDEX_NAME = '{old_idx}'"
                )
            ).scalar()
            if has_old:
                conn.execute(text(f"ALTER TABLE {table} DROP INDEX {old_idx}"))
            conn.execute(text(f"ALTER TABLE {table} ADD KEY {new_idx} (user_id, task_date)"))
            conn.commit()
            print(f"Updated {table} index to {new_idx}.")


def ensure_drop_research_id_unique() -> None:
    with _active_engine.connect() as conn:
        has_uk_users = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' "
                "AND INDEX_NAME = 'uk_users_research_id'"
            )
        ).scalar()
        if has_uk_users:
            conn.execute(text("ALTER TABLE users DROP INDEX uk_users_research_id"))
            conn.execute(text("ALTER TABLE users ADD KEY idx_users_research_id (research_id)"))
            conn.commit()
            print("Replaced users.uk_users_research_id with idx_users_research_id.")

        has_uk_baseline = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'baseline_profiles' "
                "AND INDEX_NAME = 'uk_baseline_research_id'"
            )
        ).scalar()
        if has_uk_baseline:
            conn.execute(text("ALTER TABLE baseline_profiles DROP INDEX uk_baseline_research_id"))
            conn.execute(
                text("ALTER TABLE baseline_profiles ADD KEY idx_baseline_research_id (research_id)")
            )
            conn.commit()
            print("Replaced baseline_profiles.uk_baseline_research_id with idx_baseline_research_id.")


def ensure_web_users_participation_constraints() -> None:
    """ema_web：去掉 user_name 唯一；补充 (id, research_id) 唯一，支持同名多轮参与。"""
    with _active_engine.connect() as conn:
        has_user_name = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' "
                "AND COLUMN_NAME = 'user_name'"
            )
        ).scalar()
        if not has_user_name:
            return

        # 找出仅包含 user_name 的唯一索引并删除
        unique_indexes = conn.execute(
            text(
                "SELECT DISTINCT INDEX_NAME FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' "
                "AND NON_UNIQUE = 0 AND INDEX_NAME != 'PRIMARY'"
            )
        ).fetchall()
        for (index_name,) in unique_indexes:
            cols = [
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT COLUMN_NAME FROM information_schema.STATISTICS "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' "
                        "AND INDEX_NAME = :idx ORDER BY SEQ_IN_INDEX"
                    ),
                    {"idx": index_name},
                ).fetchall()
            ]
            if cols == ["user_name"]:
                conn.execute(text(f"ALTER TABLE users DROP INDEX `{index_name}`"))
                conn.commit()
                print(f"Dropped unique index users.{index_name} on user_name.")

        # 普通索引保留，便于按登录名查询
        has_name_idx = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' "
                "AND INDEX_NAME = 'idx_users_user_name'"
            )
        ).scalar()
        if not has_name_idx:
            conn.execute(text("ALTER TABLE users ADD KEY idx_users_user_name (user_name)"))
            conn.commit()
            print("Added users.idx_users_user_name.")

        has_uk = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' "
                "AND INDEX_NAME = 'uk_users_id_research_id'"
            )
        ).scalar()
        if not has_uk:
            conn.execute(
                text(
                    "ALTER TABLE users ADD UNIQUE KEY uk_users_id_research_id (id, research_id)"
                )
            )
            conn.commit()
            print("Added users.uk_users_id_research_id (id, research_id).")


def ensure_drop_user_login_logs_user_name() -> None:
    """web：user_login_logs 不再冗余 user_name，仅保留 user_id。"""
    with _active_engine.connect() as conn:
        has_col = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_login_logs' "
                "AND COLUMN_NAME = 'user_name'"
            )
        ).scalar()
        if not has_col:
            return
        # 先删依赖该列的索引
        indexes = conn.execute(
            text(
                "SELECT DISTINCT INDEX_NAME FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_login_logs' "
                "AND COLUMN_NAME = 'user_name' AND INDEX_NAME != 'PRIMARY'"
            )
        ).fetchall()
        for (index_name,) in indexes:
            # 仅当索引只含 user_name，或必须为删列而先 drop
            conn.execute(text(f"ALTER TABLE user_login_logs DROP INDEX `{index_name}`"))
            conn.commit()
            print(f"Dropped user_login_logs index {index_name}.")
        conn.execute(text("ALTER TABLE user_login_logs DROP COLUMN user_name"))
        conn.commit()
        print("Dropped user_login_logs.user_name column.")


def ensure_user_login_logs_client_type() -> None:
    """ema_web：为 user_login_logs 补充 client_type 列。"""
    with _active_engine.connect() as conn:
        has_col = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_login_logs' "
                "AND COLUMN_NAME = 'client_type'"
            )
        ).scalar()
        if has_col:
            return
        conn.execute(
            text(
                "ALTER TABLE user_login_logs "
                "ADD COLUMN client_type VARCHAR(16) NOT NULL DEFAULT 'web' "
                "COMMENT '终端类型：wechat / web / app' AFTER user_id"
            )
        )
        conn.commit()
        print("Added user_login_logs.client_type column.")
        has_idx = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_login_logs' "
                "AND INDEX_NAME = 'idx_login_log_client'"
            )
        ).scalar()
        if not has_idx:
            conn.execute(
                text("ALTER TABLE user_login_logs ADD KEY idx_login_log_client (client_type)")
            )
            conn.commit()
            print("Added user_login_logs.idx_login_log_client.")


def ensure_web_admin_user(client_type: str) -> None:
    """ema_web：默认管理员 admin / 123456 / role=0。"""
    if client_type != CLIENT_TYPE_WEB:
        return
    from app.database import get_session_factory
    from app.models.web import User

    db = get_session_factory(client_type)()
    try:
        if db.query(User).filter(User.user_name == "admin").first():
            return
        db.add(
            User(
                user_name="admin",
                psw="123456",
                role=0,
                study_status="active",
                login_count=0,
            )
        )
        db.commit()
        print("Seeded default web admin user (user_name=admin, psw=123456, role=0).")
    finally:
        db.close()


def main() -> None:
    global _active_engine
    ensure_database()
    # 三端共用 ema_web：只初始化一次
    eng = get_engine(CLIENT_TYPE_WEB)
    _active_engine = eng
    print("--- Initializing tables for shared ema_web ---")
    get_base(CLIENT_TYPE_WEB).metadata.create_all(bind=eng)
    ensure_session_key_column()
    ensure_logout_at_column()
    ensure_user_login_logs_client_type()
    ensure_risk_session_columns()
    ensure_feedback_session_columns()
    ensure_baseline_completed_at_column()
    ensure_ms_to_datetime_columns()
    ensure_users_logout_at_and_openid_index()
    ensure_feature_session_columns()
    ensure_drop_research_id_unique()
    ensure_web_users_participation_constraints()
    ensure_drop_user_login_logs_user_name()
    ensure_web_admin_user(CLIENT_TYPE_WEB)
    print("Tables created successfully for shared ema_web.")


if __name__ == "__main__":
    main()
