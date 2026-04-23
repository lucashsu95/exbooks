import random
import itertools

import factory
from django.contrib.auth.models import User

from accounts.models import TrustLevelConfig, UserProfile
from books.models import BookPhoto, BookSet, OfficialBook, SharedBook, WishListItem
from deals.models import Deal, DealMessage, LoanExtension, Notification, Rating


# 台灣常見教科書與參考書資料
TEXTBOOK_DATA = {
    "titles": [
        "國文（二）",
        "國文（三）",
        "國文（四）",
        "國文（五）",
        "數學（國二）",
        "數學（國三）",
        "數學（高一）",
        "數學（高二）",
        "英文（二）",
        "英文（三）",
        "物理（高一）",
        "物理（高二）",
        "化學（高一）",
        "化學（高二）",
        "生物（高一）",
        "生物（高二）",
        "歷史（台灣史）",
        "歷史（中國史）",
        "地理（台灣地理）",
        "公民與社會（一）",
        "公民與社會（二）",
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
        "作文範例精選",
        "英文單字速記",
        "數學解題技巧",
        "物理實驗手冊",
        "化學實驗手冊",
    ],
    "authors": [
        "康軒編輯部",
        "翰林編輯部",
        "南一編輯部",
        "龍騰編輯部",
        "教育部",
        "國家教育研究院",
        "台灣師範大學",
        "國立編譯館",
    ],
    "publishers": [
        "康軒文教",
        "翰林出版",
        "南一書局",
        "龍騰文化",
        "大同資訊",
        "育橋出版",
        "正中書局",
        "三民書局",
    ],
}

# 台灣常見暱稱
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
]

# 無限迭代器，確保不重複
_title_cycle = itertools.cycle(TEXTBOOK_DATA["titles"])
_nickname_cycle = itertools.cycle(NICKNAMES)


def _get_next_title():
    return next(_title_cycle)


def _get_next_nickname():
    return next(_nickname_cycle)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name", locale="zh_TW")
    last_name = factory.Faker("last_name", locale="zh_TW")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class TrustLevelConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TrustLevelConfig

    level = factory.Sequence(lambda n: n)
    group_name = factory.LazyAttribute(lambda obj: f"trust_lv{obj.level}")
    display_name = factory.LazyAttribute(lambda obj: f"Level {obj.level}")
    min_score = factory.LazyAttribute(lambda obj: obj.level * 100)
    max_books = 5
    max_days = 30


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile
        django_get_or_create = ("user",)

    user = factory.SubFactory(UserFactory)
    nickname = factory.LazyAttribute(lambda _: _get_next_nickname())
    default_transferability = UserProfile.Transferability.RETURN
    default_location = "台北市信義區"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override to update the profile created by User post_save signal."""
        user = kwargs.get("user")
        if user:
            # Profile might already exist due to signal
            profile, created = model_class.objects.get_or_create(user=user)
            # Update fields with factory generated values
            for key, value in kwargs.items():
                setattr(profile, key, value)
            profile.save()
            return profile
        return super()._create(model_class, *args, **kwargs)


class OfficialBookFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OfficialBook

    isbn = factory.Sequence(lambda n: f"{9780000000000 + n}")
    title = factory.LazyAttribute(lambda _: _get_next_title())
    author = factory.LazyAttribute(lambda _: random.choice(TEXTBOOK_DATA["authors"]))
    publisher = factory.LazyAttribute(
        lambda _: random.choice(TEXTBOOK_DATA["publishers"])
    )
    description = "適合高中職學生使用，內容涵蓋課程重點與練習題。"


class BookSetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BookSet

    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"套書 {n}")
    description = factory.Faker("sentence", locale="zh_TW")


class SharedBookFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SharedBook

    official_book = factory.SubFactory(OfficialBookFactory)
    owner = factory.SubFactory(UserFactory)
    keeper = factory.LazyAttribute(lambda obj: obj.owner)
    transferability = SharedBook.Transferability.RETURN
    status = SharedBook.Status.SUSPENDED
    loan_duration_days = 30
    extend_duration_days = 14
    condition_description = "書況良好"


class BookPhotoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BookPhoto

    shared_book = factory.SubFactory(SharedBookFactory)
    uploader = factory.LazyAttribute(lambda obj: obj.shared_book.owner)
    photo = factory.django.ImageField(filename="test.jpg")
    caption = "書況照片"


class WishListItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WishListItem

    user = factory.SubFactory(UserFactory)
    official_book = factory.SubFactory(OfficialBookFactory)


class DealFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Deal

    shared_book = factory.SubFactory(SharedBookFactory)
    deal_type = Deal.DealType.LOAN
    status = Deal.Status.REQUESTED
    applicant = factory.SubFactory(UserFactory)
    responder = factory.LazyAttribute(lambda obj: obj.shared_book.owner)
    previous_book_status = factory.LazyAttribute(lambda obj: obj.shared_book.status)


class DealMessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DealMessage

    deal = factory.SubFactory(DealFactory)
    sender = factory.LazyAttribute(lambda obj: obj.deal.applicant)
    content = factory.Faker("paragraph", locale="zh_TW")


class RatingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Rating

    deal = factory.SubFactory(DealFactory)
    rater = factory.LazyAttribute(lambda obj: obj.deal.applicant)
    ratee = factory.LazyAttribute(lambda obj: obj.deal.responder)
    friendliness_score = factory.Faker("random_int", min=1, max=5)
    punctuality_score = factory.Faker("random_int", min=1, max=5)
    accuracy_score = factory.Faker("random_int", min=1, max=5)
    comment = factory.Faker("sentence", locale="zh_TW")


class LoanExtensionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LoanExtension

    deal = factory.SubFactory(DealFactory)
    requested_by = factory.LazyAttribute(lambda obj: obj.deal.applicant)
    extra_days = 14
    status = LoanExtension.Status.PENDING


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    recipient = factory.SubFactory(UserFactory)
    notification_type = Notification.NotificationType.DEAL_REQUESTED
    title = "測試通知"
    message = "這是一則測試通知"
    is_read = False
