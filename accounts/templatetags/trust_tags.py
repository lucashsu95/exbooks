from django import template
from accounts.models import TrustLevelConfig

register = template.Library()

@register.simple_tag
def get_trust_config(group_name):
    """
    根據群組名稱取得對應的 TrustLevelConfig。
    例如：'trust_lv0' -> Lv0 的 Config 物件
    """
    if group_name and group_name.startswith('trust_lv'):
        try:
            level_str = group_name[8:]
            if level_str.isdigit():
                level = int(level_str)
                return TrustLevelConfig.objects.filter(level=level).first()
        except (ValueError, TypeError):
            pass
    return None
