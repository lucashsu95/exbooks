import factory
from django.contrib.auth.models import User

from accounts.models import UserProfile
from books.models import BookPhoto, BookSet, OfficialBook, SharedBook, WishListItem
from deals.models import Deal, DealMessage, LoanExtension, Notification, Rating


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name", locale="zh_TW")
    last_name = factory.Faker("last_name", locale="zh_TW")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile
        django_get_or_create = ("user",)

    user = factory.SubFactory(UserFactory)
    nickname = factory.Faker("name", locale="zh_TW")
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
    title = factory.Faker("sentence", nb_words=4, locale="zh_TW")
    author = factory.Faker("name", locale="zh_TW")
    publisher = factory.Faker("company", locale="zh_TW")
    description = factory.Faker("paragraph", locale="zh_TW")


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
    integrity_score = factory.Faker("random_int", min=1, max=5)
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
