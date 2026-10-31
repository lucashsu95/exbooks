from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """公開頁面的 sitemap。

    書籍列表與詳情頁皆需登入（books:list / books:detail），目前沒有公開
    瀏覽路由，因此只列出首頁。
    """

    priority = 1.0
    changefreq = "weekly"

    def items(self):
        return ["landing"]

    def location(self, item):
        return reverse(item)
