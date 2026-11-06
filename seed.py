"""演示数据初始化脚本。

用法（在项目根目录，安装依赖后执行）:
    python seed.py

生成演示账号:
    admin      / Admin@123      管理员
    coach_li   / Coach@123      教练（已认证）
    coach_wang / Coach@123      教练（待审核）
    student_wx / Student@123    学员（高活跃）
    student_zy / Student@123    学员（中活跃）
    student_cj / Student@123    学员（低活跃）
"""
import random
from datetime import date, datetime, timedelta

from app.auth.security import hash_password
from app.database import db

random.seed(42)


def upsert_user(username, password, nickname, role, phone=None, streak=0):
    row = db.query("SELECT id FROM users WHERE username = %s", (username,), one=True)
    if row:
        db.execute("DELETE FROM users WHERE id = %s", (row["id"],))
    user_id = db.insert(
        "INSERT INTO users (username, password_hash, nickname, role, phone, current_streak, longest_streak, last_login_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (username, hash_password(password), nickname, role, phone,
         streak, streak, datetime.now()))
    return user_id


def seed():
    today = date.today()

    admin_id = upsert_user("admin", "Admin@123", "平台管理员", "admin")
    coach_li = upsert_user("coach_li", "Coach@123", "李教练", "coach", "13800000001")
    coach_wang = upsert_user("coach_wang", "Coach@123", "王教练", "coach", "13800000002")
    s_wx = upsert_user("student_wx", "Student@123", "王小星", "student", "13900000001", 12)
    s_zy = upsert_user("student_zy", "Student@123", "张一远", "student", "13900000002", 5)
    s_cj = upsert_user("student_cj", "Student@123", "陈静", "student", "13900000003", 2)
    s_lb = upsert_user("student_lb", "Student@123", "刘博", "student", "13900000004", 8)

    db.execute("DELETE FROM coach_profiles")
    db.insert(
        "INSERT INTO coach_profiles (user_id, real_name, bio, specialty, certifications, review_status) "
        "VALUES (%s,%s,%s,%s,%s,'approved')",
        (coach_li, "李强", "从业8年，国家一级健身教练，擅长增肌减脂与体能训练。",
         "增肌/减脂/体能", "NSCA-CPT, 国家职业资格健身教练证"))
    db.insert(
        "INSERT INTO coach_profiles (user_id, real_name, bio, specialty, certifications, review_status) "
        "VALUES (%s,%s,%s,%s,%s,'pending')",
        (coach_wang, "王磊", "CrossFit Level 2 教练，功能性训练爱好者。",
         "功能性训练/拉伸", "CrossFit Level 2"))

    # ---------- 训练计划 ----------
    students = [(s_wx, coach_li), (s_zy, coach_li), (s_cj, coach_li), (s_lb, coach_li)]
    plan_tpl = {
        s_wx: ("增肌入门 4 周计划", [("杠铃卧推", 4, 10, 40), ("哑铃飞鸟", 3, 12, 10),
                                   ("哑铃推肩", 3, 12, 8), ("平板支撑", 3, 60, 0)]),
        s_zy: ("减脂塑形 4 周计划", [("跑步机慢跑", 1, 30, 0), ("杠铃深蹲", 4, 12, 30),
                                   ("高位下拉", 3, 12, 30), ("卷腹", 3, 20, 0)]),
        s_cj: ("体态改善 2 周计划", [("高位下拉", 3, 12, 25), ("平板支撑", 3, 45, 0),
                                    ("卷腹", 3, 15, 0)]),
        s_lb: ("力量进阶 6 周计划", [("硬拉", 5, 5, 80), ("杠铃深蹲", 5, 8, 60),
                                    ("引体向上", 4, 8, 0), ("杠铃推举", 4, 8, 30)]),
    }
    plan_ids = {}
    for sid, cid in students:
        title, items = plan_tpl[sid]
        start = today - timedelta(days=20)
        end = today + timedelta(days=14)
        plan_id = db.insert(
            "INSERT INTO training_plans (coach_id, student_id, title, description, start_date, end_date, is_recommended, recommend_weight) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (cid, sid, title, "系统演示计划，可复制修改。", start, end,
             1 if sid == s_wx else 0, 90 if sid == s_wx else 0))
        plan_ids[sid] = plan_id
        for week in range(5):
            day = start + timedelta(days=week * 7 + 1)
            if day > end:
                break
            for idx, it in enumerate(items):
                name, sets_, reps, weight = it
                db.execute(
                    "INSERT INTO plan_items (plan_id, day_date, exercise_name, sets, reps, weight_suggest, rest_sec, note, sort_order) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (plan_id, day, name, sets_, reps, weight, 90, "", idx))

    # ---------- 打卡数据 ----------
    activity = {s_wx: 0.85, s_zy: 0.6, s_cj: 0.3, s_lb: 0.7}
    exercise_pool = ["杠铃卧推", "哑铃飞鸟", "引体向上", "杠铃深蹲", "硬拉", "杠铃划船",
                     "哑铃推肩", "平板支撑", "跑步机慢跑", "动感单车"]
    for sid, rate in activity.items():
        for i in range(59, -1, -1):
            d = today - timedelta(days=i)
            if random.random() > rate:
                continue
            volume = random.randint(1500, 8000)
            duration = random.randint(30, 110)
            intensity = min(5, max(1, volume // 2000))
            checkin_id = db.insert(
                "INSERT INTO checkins (user_id, checkin_date, content, plan_id, train_volume, duration_min, intensity) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (sid, d, random.choice([
                    "今天状态不错，完成度很高！", "有点累但坚持下来了。", "训练加量，明天加油。",
                    "按计划完成训练，组间休息严格控制。", "有氧日，跑完很舒畅。"]),
                 plan_ids.get(sid), volume, duration, intensity))
            for name in random.sample(exercise_pool, random.randint(2, 4)):
                sets_ = random.randint(3, 5)
                reps = random.randint(8, 15)
                weight = random.randint(10, 70)
                db.execute(
                    "INSERT INTO checkin_details (checkin_id, exercise_name, sets, reps, weight, rpe, heart_rate, rest_sec) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (checkin_id, name, sets_, reps, weight, random.randint(6, 9),
                     random.randint(120, 165), random.randint(60, 120)))

    # ---------- 身体数据 ----------
    body_base = {s_wx: (72.5, 18.0), s_zy: (65.0, 24.5), s_cj: (55.0, 27.0), s_lb: (80.0, 16.5)}
    for sid, (w0, fat0) in body_base.items():
        for i in range(8, -1, -1):
            d = today - timedelta(days=i * 7)
            w = round(w0 - (8 - i) * random.uniform(0.1, 0.4), 1)
            fat = round(fat0 - (8 - i) * random.uniform(0.05, 0.25), 1)
            db.execute(
                "INSERT INTO body_records (user_id, record_date, weight, body_fat, chest, waist, hip, arm, thigh) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (sid, d, w, fat, round(w * 1.32, 1), round(w * 0.78, 1), round(w * 0.98, 1),
                 round(w * 0.35, 1), round(w * 0.56, 1)))

    # ---------- 社区动态 ----------
    db.execute("DELETE FROM community_posts")
    posts = [
        (s_wx, "第 12 天打卡！高位下拉终于能拉起 45kg 了，背部发力感越来越明显 💪", "public"),
        (s_zy, "有氧日，5 公里跑完，配速比上周快了 20 秒，继续加油！", "public"),
        (s_cj, "今天状态一般，只完成了计划的一半，明天补上。", "coach"),
        (s_lb, "硬拉冲到 100kg×5！下周目标 105kg。", "public"),
        (coach_li, "训练小知识：做高位下拉时想象用肘部「向下插口袋」，而不是用手拉杆，背阔肌发力会更充分。", "public"),
    ]
    for uid, content, vis in posts:
        db.insert(
            "INSERT INTO community_posts (user_id, content, visibility) VALUES (%s,%s,%s)",
            (uid, content, vis))

    # ---------- 成就 ----------
    db.execute("DELETE FROM achievements")
    for r in db.query("SELECT id, current_streak FROM users WHERE role='student'"):
        if r["current_streak"] >= 7:
            db.execute("INSERT INTO achievements (user_id, badge_code) VALUES (%s,'streak_7')", (r["id"],))
            db.execute("INSERT IGNORE INTO achievements (user_id, badge_code) VALUES (%s,'total_30')", (r["id"],))

    # ---------- 消息 ----------
    db.execute("DELETE FROM messages")
    for sid, _ in students:
        db.execute(
            "INSERT INTO messages (sender_id, receiver_id, msg_type, content) VALUES (%s,%s,'text',%s)",
            (coach_li, sid, "本周计划已更新，注意训练前充分热身。"))
        db.execute(
            "INSERT INTO messages (sender_id, receiver_id, msg_type, content, is_read) VALUES (NULL,%s,'system',%s,1)",
            (sid, "欢迎使用健身打卡追踪器，坚持每天打卡！"))

    # ---------- 补签申请 ----------
    db.execute("DELETE FROM makeup_requests")
    db.execute(
        "INSERT INTO makeup_requests (user_id, checkin_date, reason) VALUES (%s,%s,%s)",
        (s_zy, today - timedelta(days=2), "出差漏打卡，实际已完成训练。"))
    db.execute(
        "INSERT INTO makeup_requests (user_id, checkin_date, reason) VALUES (%s,%s,%s)",
        (s_cj, today - timedelta(days=4), "生病休息，补录居家训练。"))

    # ---------- 操作日志 ----------
    db.execute("DELETE FROM operation_logs")
    db.execute(
        "INSERT INTO operation_logs (admin_id, module, action, detail) VALUES (%s,'系统','初始化','seed.py 生成演示数据')",
        (admin_id,))

    # 重新计算连续打卡
    from app.services.checkin_service import recompute_streak
    for sid, _ in students:
        recompute_streak(sid)

    print("演示数据初始化完成。")
    print("账号: admin/Admin@123, coach_li/Coach@123, coach_wang/Coach@123, "
          "student_wx/Student@123, student_zy/Student@123, student_cj/Student@123")


if __name__ == "__main__":
    seed()
