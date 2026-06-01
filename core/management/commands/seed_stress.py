"""
大量資料填充指令 — 用 bulk_create 快速產生數千筆測試資料。

使用方式：
    # 基本用法
    python manage.py seed_stress --scale medium

    # 自訂參數
    python manage.py seed_stress --users 100 --books 500 --shared 1000

    # 含書況照片
    python manage.py seed_stress --scale large --photos 3

    # 不蓋既有資料
    python manage.py seed_stress --scale large --keep-existing

    # 只有 timing 報告，不寫入資料
    python manage.py seed_stress --scale xlarge --dry-run
"""

import random
import time
from dataclasses import dataclass

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import UserProfile
from books.models import BookPhoto, OfficialBook, SharedBook
from deals.models import Deal, DealMessage, LoanExtension, Notification, Rating

# ── 台灣教科書資料（與 factories.py 共用風格） ──────────────────────

TEXTBOOK_TITLES = [
    "國文（二）",
    "國文（三）",
    "數學（高一）",
    "英文（二）",
    "物理（高一）",
    "化學（高一）",
    "生物（高一）",
    "歷史（台灣史）",
    "地理（台灣地理）",
    "公民與社會（一）",
    "地球科學",
    "基礎物理",
    "基礎化學",
    "基礎生物",
    "選修物理（上）",
    "選修化學（上）",
    "選修生物（上）",
    "高中英文閱讀測驗",
    "高中數學演練",
    "國文閱讀理解",
    "微積分",
    "線性代數",
    "資料結構",
    "演算法",
    "作業系統",
    "計算機網路",
    "資料庫系統",
    "軟體工程",
    "程式設計（Python）",
    "程式設計（Java）",
    "離散數學",
    "機率與統計",
    "電子學",
    "電路學",
    "經濟學原理",
    "會計學",
    "管理學",
    "統計學",
    "心理學導論",
    "社會學導論",
    "哲學導論",
    "法學緒論",
    "圖解 Django",
    "Python 自動化的樂趣",
    "流暢的 Python",
    "Clean Code 無瑕的程式碼",
    "Design Pattern 設計模式",
    "深入淺出 Kubernetes",
    "Docker 實戰",
    "SQL 經典教程",
]

AUTHORS = [
    "康軒編輯部",
    "翰林編輯部",
    "南一編輯部",
    "龍騰編輯部",
    "教育部",
    "國家教育研究院",
    "台灣師範大學",
    "國立編譯館",
    "陳老師",
    "林教授",
    "王博士",
    "張研究員",
    "黃工程師",
    "洪教授",
    "趙博士",
    "周老師",
    "吳主任",
    "鄭研究員",
]

PUBLISHERS = [
    "康軒文教",
    "翰林出版",
    "南一書局",
    "龍騰文化",
    "大同資訊",
    "育橋出版",
    "正中書局",
    "三民書局",
    "碁峰資訊",
    "歐萊禮",
    "博碩文化",
    "深智數位",
    "全華圖書",
    "高立圖書",
    "東華書局",
    "學貫行銷",
]

NICKNAMES = [
    "小明",
    "小華",
    "阿豪",
    "小美",
    "阿傑",
    "小婷",
    "阿瑋",
    "小玲",
    "阿哲",
    "小雯",
    "阿翔",
    "小茹",
    "阿霖",
    "小君",
    "阿欣",
    "小娟",
    "阿宏",
    "小芳",
    "阿賢",
    "小琪",
    "大寶",
    "小寶",
    "阿中",
    "小艾",
    "阿德",
    "小可",
    "阿志",
    "小希",
    "阿文",
    "小瑜",
]

LOCATIONS = [
    "台北市中正區",
    "台北市大安區",
    "台北市信義區",
    "新北市板橋區",
    "新北市永和區",
    "桃園市中壢區",
    "新竹市東區",
    "台中市西區",
    "台中市北區",
    "台南市中西區",
    "高雄市苓雅區",
    "高雄市左營區",
]

BOOK_CATEGORIES = [c[0] for c in OfficialBook.Category.choices]

SHARED_STATUSES = [
    SharedBook.Status.TRANSFERABLE,
    SharedBook.Status.OCCUPIED,
]

TRANSFERABILITY_CHOICES = [
    SharedBook.Transferability.RETURN,
]

DEAL_TYPES = [Deal.DealType.LOAN, Deal.DealType.TRANSFER]

# ── Scale 預設 ─────────────────────────────────────────────────────

SCALES = {
    "small": {"users": 10, "books": 20, "shared": 30},
    "medium": {"users": 100, "books": 500, "shared": 1000},
    "large": {"users": 500, "books": 2000, "shared": 5000},
    "xlarge": {"users": 1000, "books": 5000, "shared": 10000},
}

# ── 計時器 ─────────────────────────────────────────────────────────


@dataclass
class Timing:
    label: str
    elapsed: float
    count: int

    @property
    def per_sec(self) -> str:
        if self.elapsed > 0:
            return f"{self.count / self.elapsed:.0f}/s"
        return "-"


class Timers:
    def __init__(self):
        self._records: list[Timing] = []

    def record(self, label: str, count: int):
        self._records.append(Timing(label, 0, count))

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self._elapsed = time.perf_counter() - self._start

    def done(self, label: str, count: int):
        self._records.append(Timing(label, self._elapsed, count))

    def report(self) -> list[str]:
        lines = []
        lines.append(f"{'Phase':<40} {'Count':>8} {'Time':>8} {'Rate':>10}")
        lines.append("-" * 68)
        total_time = 0
        total_count = 0
        for t in self._records:
            lines.append(
                f"{t.label:<40} {t.count:>8} {t.elapsed:>7.2f}s {t.per_sec:>10}"
            )
            total_time += t.elapsed
            total_count += t.count
        lines.append("-" * 68)
        if total_time > 0:
            lines.append(
                f"{'TOTAL':<40} {total_count:>8} {total_time:>7.2f}s "
                f"{total_count / total_time:>8.0f}/s"
            )
        return lines


# ── Command ────────────────────────────────────────────────────────


class Command(BaseCommand):
    help = "大量資料填充 — 使用 bulk_create 快速產生測試資料"

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=None,
            help="用戶數量 (default: 依 scale 決定)",
        )
        parser.add_argument(
            "--books",
            type=int,
            default=None,
            help="官方書目數量 (default: 依 scale 決定)",
        )
        parser.add_argument(
            "--shared",
            type=int,
            default=None,
            help="共享書籍數量 (default: 依 scale 決定)",
        )
        parser.add_argument(
            "--deals",
            type=float,
            default=0.5,
            help="有交易的共享書比例 (0.0~1.0, default: 0.5)",
        )
        parser.add_argument(
            "--photos",
            type=int,
            default=0,
            help="每本共享書的照片數量 (default: 0, 不產生真實圖片)",
        )
        parser.add_argument(
            "--scale",
            type=str,
            choices=list(SCALES),
            default="medium",
            help="預設規模 (default: medium)",
        )
        parser.add_argument(
            "--keep-existing",
            action="store_true",
            default=False,
            help="不先清空既有資料 (default: 清空)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="只計算不寫入 (用於預覽資料量)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="bulk_create 批次大小 (default: 500)",
        )

    def handle(self, *args, **options):
        scale = options["scale"]
        scale_cfg = SCALES[scale]

        num_users = options["users"] or scale_cfg["users"]
        num_books = options["books"] or scale_cfg["books"]
        num_shared = options["shared"] or scale_cfg["shared"]
        deal_ratio = options["deals"]
        photos_per_book = options["photos"]
        keep_existing = options["keep_existing"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        if not 0.0 <= deal_ratio <= 1.0:
            self.stderr.write("--deals 必須在 0.0 ~ 1.0 之間")
            return

        self.stdout.write(
            self.style.WARNING(
                f"Scale: {scale} | "
                f"Users: {num_users} | Books: {num_books} | "
                f"Shared: {num_shared} | Deals: {deal_ratio:.0%} | "
                f"Photos/Book: {photos_per_book}"
            )
        )
        target_deals = int(num_shared * deal_ratio)
        target_photos = num_shared * photos_per_book
        self.stdout.write(
            f"Target: ~{num_users:,} users, {num_books:,} books, "
            f"{num_shared:,} shared, {target_deals:,} deals, "
            f"{target_photos:,} photos"
        )

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry-run mode. 未寫入任何資料。"))
            return

        timers = Timers()

        # -----------------------------------------------------------
        # Phase 0: 清空既有資料
        # -----------------------------------------------------------
        if not keep_existing:
            with timers:
                self._clear_data()
            timers.done("0. Clear existing data", 0)

        # -----------------------------------------------------------
        # Phase 1: Users + UserProfiles (無 FK 依賴)
        # -----------------------------------------------------------
        with timers:
            self._create_users(num_users, batch_size)
        timers.done("1. Create users", num_users)

        # -----------------------------------------------------------
        # Phase 2: OfficialBooks (無 FK 依賴)
        # -----------------------------------------------------------
        with timers:
            self._create_books(num_books, batch_size)
        timers.done("2. Create official books", num_books)

        # -----------------------------------------------------------
        # Phase 3: SharedBooks (FK → OfficialBook, User)
        # -----------------------------------------------------------
        with timers:
            self._create_shared_books(num_shared, batch_size)
        timers.done("3. Create shared books", num_shared)

        # -----------------------------------------------------------
        # Phase 4: Deals (FK → SharedBook, User)
        # -----------------------------------------------------------
        if target_deals > 0:
            with timers:
                self._create_deals(target_deals, batch_size)
            timers.done("4. Create deals", target_deals)

        # -----------------------------------------------------------
        # Phase 5: BookPhotos (FK → SharedBook, User) — 不產生真實檔案
        # -----------------------------------------------------------
        if photos_per_book > 0:
            with timers:
                self._create_photos(photos_per_book, batch_size)
            timers.done("5. Create book photos", target_photos)

        # -----------------------------------------------------------
        # 報告
        # -----------------------------------------------------------
        self.stdout.write("")
        for line in timers.report():
            self.stdout.write(line)
        self.stdout.write("")

        # 總筆數確認
        final_counts = self._count_all()
        self.stdout.write(self.style.SUCCESS("Final record counts:"))
        for label, count in final_counts:
            self.stdout.write(f"  {label:<35} {count:>8,}")

    # ── Clear ──────────────────────────────────────────────────────

    def _clear_data(self):
        with transaction.atomic():
            BookPhoto.objects.all().delete()
            LoanExtension.objects.all().delete()
            DealMessage.objects.all().delete()
            Rating.objects.all().delete()
            Notification.objects.all().delete()
            Deal.objects.all().delete()
            SharedBook.objects.all().delete()
            OfficialBook.objects.all().delete()
            UserProfile.objects.filter(user__is_superuser=False).delete()
            User.objects.filter(is_superuser=False).delete()

    # ── Create Users ──────────────────────────────────────────────

    def _create_users(self, count: int, batch_size: int):
        # 預先 hash 密碼一次，避免每個使用者重複 bcrypt
        hashed_password = make_password("testpass123")
        users = []
        profiles = []
        for i in range(count):
            username = f"user{i}"
            u = User(
                username=username,
                email=f"{username}@exbooks.test",
                password=hashed_password,
                first_name="",
                last_name="",
                date_joined="2025-01-01 00:00:00+00:00"
                if i % 2 == 0
                else "2025-06-15 00:00:00+00:00",
            )
            u.id = i + 1  # 手動指定 PK，方便關聯
            users.append(u)

            p = UserProfile(
                user_id=u.id,
                nickname=NICKNAMES[i % len(NICKNAMES)],
                default_transferability=random.choice(
                    [
                        UserProfile.Transferability.RETURN,
                        UserProfile.Transferability.TRANSFER,
                    ]
                ),
                default_location=random.choice(LOCATIONS),
                trust_score=random.randint(0, 100),
            )
            profiles.append(p)

        # User
        User.objects.bulk_create(users, batch_size=batch_size)

        # 因為 User 的 post_save signal 會自動建立 UserProfile，
        # 但 bulk_create 不觸發 signal，所以要手動建立。
        # 同時 signal 可能在 migrate 時建立了 TrustLevelConfig，
        # 而 UserProfile 保留給我們手動建立。
        # 為了避免 signal 干擾，先把既有 profile 刪掉再 bulk_create
        # （第一個 user 可能因為 migrate 的關係已經有 profile）
        created_ids = [u.id for u in users]
        UserProfile.objects.filter(user_id__in=created_ids).delete()
        UserProfile.objects.bulk_create(profiles, batch_size=batch_size)

    # ── Create OfficialBooks ──────────────────────────────────────

    def _create_books(self, count: int, batch_size: int):
        books = []
        for i in range(count):
            title = TEXTBOOK_TITLES[i % len(TEXTBOOK_TITLES)]
            if i >= len(TEXTBOOK_TITLES):
                title = f"{title} ({i // len(TEXTBOOK_TITLES) + 1})"

            b = OfficialBook(
                isbn=str(9780000000000 + i),
                title=title,
                author=random.choice(AUTHORS),
                publisher=random.choice(PUBLISHERS),
                category=random.choice(BOOK_CATEGORIES),
                description="壓力測試用書目資料，內容僅供效能測試參考。",
            )
            b.id = i + 1
            books.append(b)

        OfficialBook.objects.bulk_create(books, batch_size=batch_size)

    # ── Create SharedBooks ────────────────────────────────────────

    def _create_shared_books(self, count: int, batch_size: int):
        user_ids = list(
            User.objects.filter(is_superuser=False).values_list("id", flat=True)[:count]
        )
        book_ids = list(OfficialBook.objects.values_list("id", flat=True)[:count])

        shared_books = []
        for i in range(count):
            owner_id = random.choice(user_ids)
            status = random.choices(
                SHARED_STATUSES,
                weights=[0.7, 0.3],  # 70% TRANSFERABLE, 30% OCCUPIED
            )[0]

            sb = SharedBook(
                official_book_id=random.choice(book_ids),
                owner_id=owner_id,
                keeper_id=owner_id,
                transferability=random.choice(TRANSFERABILITY_CHOICES),
                status=status,
                loan_duration_days=random.randint(15, 90),
                extend_duration_days=random.choice([7, 14, 21, 30]),
                condition_description="書況良好，無破損",
            )
            shared_books.append(sb)

        SharedBook.objects.bulk_create(shared_books, batch_size=batch_size)

    # ── Create Deals ──────────────────────────────────────────────

    def _create_deals(self, count: int, batch_size: int):
        occupied_ids = list(
            SharedBook.objects.filter(status=SharedBook.Status.OCCUPIED).values_list(
                "id", "keeper_id", "owner_id"
            )
        )

        if not occupied_ids:
            self.stdout.write(
                self.style.WARNING("沒有 OCCUPIED 的共享書，跳過交易建立。")
            )
            return

        user_ids = list(
            User.objects.filter(is_superuser=False).values_list("id", flat=True)
        )

        deals = []
        deal_count = min(count, len(occupied_ids))
        for sb_id, keeper_id, owner_id in occupied_ids[:deal_count]:
            other_users = [uid for uid in user_ids if uid != owner_id]
            if not other_users:
                continue

            d = Deal(
                shared_book_id=sb_id,
                deal_type=random.choice(DEAL_TYPES),
                status=Deal.Status.MEETED,
                applicant_id=random.choice(other_users),
                responder_id=owner_id,
                previous_book_status=SharedBook.Status.TRANSFERABLE,
            )
            deals.append(d)

        Deal.objects.bulk_create(deals, batch_size=batch_size)

    # ── Create BookPhotos (不產生真實檔案) ────────────────────────

    def _create_photos(self, photos_per_book: int, batch_size: int):
        # 不產生真實圖片檔案，photo 設為空字串避免浪費磁碟
        shared_ids = list(SharedBook.objects.values_list("id", "owner_id"))

        photos = []
        for sb_id, owner_id in shared_ids:
            for _ in range(photos_per_book):
                p = BookPhoto(
                    shared_book_id=sb_id,
                    uploader_id=owner_id,
                    photo="",  # 無真實檔案
                    caption="壓力測試用書況照片",
                )
                photos.append(p)

        BookPhoto.objects.bulk_create(photos, batch_size=batch_size)

    # ── Count ─────────────────────────────────────────────────────

    def _count_all(self):
        return [
            ("User", User.objects.count()),
            ("UserProfile", UserProfile.objects.count()),
            ("OfficialBook", OfficialBook.objects.count()),
            ("SharedBook", SharedBook.objects.count()),
            ("Deal", Deal.objects.count()),
            ("BookPhoto", BookPhoto.objects.count()),
        ]
