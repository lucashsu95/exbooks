from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import SharedBook


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = "weekly"

    def items(self):
        return ["landing", "public_browse"]

    def location(self, item):
        if item == "landing":
            return reverse("landing")
        return reverse("books:public_list")


class PublicSharedBookSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return (
            SharedBook.objects.filter(status=SharedBook.Status.TRANSFERABLE)
            .select_related("official_book")
            .order_by("-updated_at")
        )

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("books:public_detail", kwargs={"pk": obj.pk})
