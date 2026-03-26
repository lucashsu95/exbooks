"""
產生 VAPID 金鑰用於 Web Push 通知。

VAPID (Voluntary Application Server Identification) 是 Web Push 協議的一部分，
用於識別發送 Push 通知的應用伺服器。

使用方式：
    python manage.py generate_vapid_keys

產生的金鑰會儲存到資料庫（WebPushConfig 表），
同時也會輸出環境變數格式供 .env 檔案使用。
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from deals.models import WebPushConfig


class Command(BaseCommand):
    help = "產生 VAPID 金鑰用於 Web Push 通知"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="強制重新產生金鑰（覆蓋現有設定）",
        )
        parser.add_argument(
            "--subject",
            type=str,
            default="mailto:exbooks@example.com",
            help="VAPID subject（聯絡信箱或網站 URL）",
        )

    def handle(self, *args, **options):
        force = options["force"]
        subject = options["subject"]

        # 檢查是否已有設定
        existing_config = WebPushConfig.get_config()
        if existing_config and not force:
            self.stdout.write(
                self.style.WARNING(
                    "VAPID 金鑰已存在。使用 --force 參數可強制重新產生。"
                )
            )
            self.stdout.write(f"\n現有公開金鑰: {existing_config.vapid_public_key}")
            self.stdout.write(f"Subject: {existing_config.subject}")
            return

        # 嘗試使用 cryptography 套件產生金鑰
        try:
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            import base64

            # 產生 P-256 ECDH 金鑰對
            private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())

            # 取得私有金鑰（DER 格式，base64 編碼）
            private_key_der = private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            private_key_b64 = (
                base64.urlsafe_b64encode(private_key_der).decode("utf-8").rstrip("=")
            )

            # 取得公開金鑰（未壓縮格式，65 bytes）
            public_key = private_key.public_key()
            public_key_raw = public_key.public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint,
            )
            public_key_b64 = (
                base64.urlsafe_b64encode(public_key_raw).decode("utf-8").rstrip("=")
            )

        except ImportError:
            self.stdout.write(
                self.style.ERROR(
                    "需要 'cryptography' 套件來產生 VAPID 金鑰。\n"
                    "請執行: pip install cryptography\n"
                    "\n"
                    "或者，您可以使用以下線上工具產生金鑰：\n"
                    "https://tools.reactpwa.com/vapid\n"
                    "https://vapidkeys.com/\n"
                    "\n"
                    "產生後，請手動設定環境變數：\n"
                    "VAPID_PUBLIC_KEY=<您的公開金鑰>\n"
                    "VAPID_PRIVATE_KEY=<您的私有金鑰>"
                )
            )
            return

        # 儲存到資料庫
        with transaction.atomic():
            if existing_config:
                existing_config.vapid_public_key = public_key_b64
                existing_config.vapid_private_key = private_key_b64
                existing_config.subject = subject
                existing_config.save()
                config = existing_config
                self.stdout.write(self.style.SUCCESS("VAPID 金鑰已更新！"))
            else:
                config = WebPushConfig.objects.create(
                    vapid_public_key=public_key_b64,
                    vapid_private_key=private_key_b64,
                    subject=subject,
                )
                self.stdout.write(self.style.SUCCESS("VAPID 金鑰已產生並儲存！"))

        # 輸出結果
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("VAPID 金鑰設定完成"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"\n公開金鑰 (VAPID_PUBLIC_KEY):\n{config.vapid_public_key}")
        self.stdout.write("\n私有金鑰 (VAPID_PRIVATE_KEY):")
        self.stdout.write(self.style.WARNING("[已隱藏，請查看資料庫或環境變數]"))
        self.stdout.write(f"\nSubject: {config.subject}")

        self.stdout.write("\n" + "-" * 60)
        self.stdout.write("請將以下內容加入 .env 檔案：")
        self.stdout.write("-" * 60)
        self.stdout.write(f"\nVAPID_PUBLIC_KEY={config.vapid_public_key}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={config.vapid_private_key}")
        self.stdout.write(f"VAPID_SUBJECT={subject}")

        self.stdout.write("\n" + "-" * 60)
        self.stdout.write("前端 JavaScript 使用方式：")
        self.stdout.write("-" * 60)
        self.stdout.write(f"""
// 在 service worker 註冊時使用
const subscription = await registration.pushManager.subscribe({{
  userVisibleOnly: true,
  applicationServerKey: urlBase64ToUint8Array('{config.vapid_public_key}')
}});
""")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.WARNING("⚠️  警告：私有金鑰請妥善保管，切勿洩漏！"))
        self.stdout.write("=" * 60)
