#!/usr/bin/env python3
"""Fill in PO file translations for zh_Hant (passthrough) and en (English)."""

import polib
import re

ZH_HANT_PO = "locale/zh_Hant/LC_MESSAGES/django.po"
EN_PO = "locale/en/LC_MESSAGES/django.po"


def fill_zh_hant():
    """zh_Hant: copy msgid to msgstr (source is already Chinese)."""
    po = polib.pofile(ZH_HANT_PO)
    count = 0
    for entry in po:
        if entry.msgid and not entry.msgstr:
            entry.msgstr = entry.msgid
            count += 1
    po.save()
    print(f"zh_Hant: filled {count} translations")


def translate_chinese_to_english(text: str) -> str:
    """Translate a Chinese string to English using patterns + dictionary."""
    # Simple patterns
    if text.startswith("Exbooks") and not re.search(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', text):
        return text  # Already English (no CJK chars)
    if text.startswith("CSS"):
        return text
    if text.startswith("Google"):
        return text
    if text.startswith("User"):
        return text
    if text.startswith("Back to"):
        return text  # Already English
    if text == "English":
        return "English"
    if text == "Email":
        return "Email"
    if text == "Confirm":
        return "Confirm"
    if text == "ISBN":
        return "ISBN"
    if text == "Sign In":
        return "Sign In"
    if text == "Sign Up":
        return "Sign Up"

    # Django admin / allauth strings that are already partially English
    if "Confirmation" in text or "Verify" in text:
        return text

    # Large translation dict
    translations = {
        # Login / Registration
        "Email": "Email",
        "密碼": "Password",
        "登入": "Log In",
        "暱稱": "Nickname",
        "顯示在平台上的名稱": "Display Name",
        "出生日期": "Date of Birth",
        "用於年齡驗證（需年滿 18 歲）": "For age verification (must be 18+)",
        "再次確認密碼": "Confirm Password",
        "你的暱稱": "Your Nickname",
        "註冊": "Register",
        "預設取書地點": "Default Meetup Location",
        "例如：台北市大安區": "e.g., Da'an District, Taipei",
        "完成註冊": "Complete Registration",
        "儲存並繼續": "Save & Continue",
        "完善個人資料": "Complete Profile",
        "立即免費註冊": "Register Free Now",
        
        # Violation types
        "輕微": "Minor",
        "中等": "Medium",
        "嚴重": "Severe",
        "警告": "Warning",
        "暫時停權": "Temporary Suspension",
        "永久停權": "Permanent Ban",
        "未依約定面交": "Missed Meetup",
        "延遲歸還": "Late Return",
        "書況描述不符": "Book Condition Mismatch",
        "無正當理由取消": "Unjustified Cancellation",
        "詐欺": "Fraud",
        "騷擾": "Harassment",
        "惡意破壞": "Malicious Damage",
        "冒用身份": "Identity Theft",
        "其他": "Other",
        
        # Violation management
        "違規用戶": "Violating User",
        "處分類型": "Penalty Type",
        "違規等級": "Violation Level",
        "違規行為": "Violation Type",
        "違規描述": "Description",
        "停權天數": "Suspension Days",
        "暫時停權時必填，7-30 天": "Required for temporary suspension, 7-30 days",
        "是否生效中": "Active",
        "警告永遠生效；停權在期滿或解除後設為 False": "Warning is permanent; suspension set to False after expiry",
        "相關申訴": "Related Appeals",
        "違規次數": "Violation Count",
        "處分者": "Issued By",
        "違規處分": "Violation Penalty",
        "限制中": "Restricted",
        "部分功能受限": "Some Features Restricted",
        "等級保護起始時間": "Level Protection Start",
        "降級保護週數": "Demotion Protection (Weeks)",
        "記錄用戶積分跌破門檻後，降級保護期開始計時的時間點": "Timestamp when demotion protection started after score dropped below threshold",
        "達到此等級後的保護期限，期間內若積分不足也不會降級": "Protection period after reaching this level; won't be demoted even if score drops",
        "對應群組名稱": "Corresponding Group Name",
        "等級": "Level",
        "當下等級（0-3）": "Current Level (0-3)",
        "當下積分": "Current Score",
        "用戶的信用積分，根據交易、評價、逾期等計算": "User trust score, calculated from deals, ratings, overdue records",
        "用戶目前是否處於停權狀態": "Whether the user is currently suspended",
        "最低信用等級": "Minimum Trust Level",
        "最低積分門檻": "Minimum Score Threshold",
        "申請者信用等級需達 0-3，0 表示不限制": "Applicant trust level must be 0-3 (0 = no restriction)",
        "公式版本": "Formula Version",
        "基準": "Baseline",
        "批次／手動重算": "Batch / Manual Recalculate",
        "詳情": "Details",
        "解除時間": "Unlock Time",
        "解除者": "Unlocked By",
        "信用積分": "Trust Score",
        "信用積分稽核": "Trust Score Audit",
        "信用等級配置": "Trust Level Config",
        "信用評價機制": "Trust & Rating System",
        "角色": "Role",
        "操作者": "Operator",
        
        # Notifications
        "通知": "Notifications",
        "通知中心": "Notification Center",
        "通知標題": "Notification Title",
        "通知訊息": "Notification Message",
        "通知類型": "Notification Type",
        "是否已讀": "Read",
        "收到交易申請": "New Deal Request",
        "收到延長申請": "New Extension Request",
        "收到新的評價": "New Rating Received",
        "收到評價": "Rating Received",
        "收到違規處分": "Violation Issued",
        "啟用 Email 通知": "Enable Email Notifications",
        "啟用推播通知": "Enable Push Notifications",
        "停用後將不會收到 Push 通知": "Push notifications will be disabled",
        "關閉後將不會收到 Email 通知": "Email notifications will be disabled",
        "關閉後將不會收到瀏覽器 Push 通知": "Browser push notifications will be disabled",
        "設定": "Settings",
        "帳號設定": "Account Settings",
        "發送者": "Sender",
        
        # Push subscription
        "Push 訂閱": "Push Subscription",
        "Push 服務的唯一端點 URL": "Push Service Endpoint URL",
        "訂閱端點": "Subscription Endpoint",
        "p256dh 金鑰": "p256dh Key",
        "auth 金鑰": "auth Key",
        "認證金鑰（16 bytes base64 編碼）": "Auth Key (16 bytes base64 encoded)",
        "用戶端的公開金鑰（ECDH P-256）": "Client Public Key (ECDH P-256)",
        "VAPID 公開金鑰": "VAPID Public Key",
        "VAPID 私有金鑰": "VAPID Private Key",
        "Web Push 設定": "Web Push Settings",
        "瀏覽器識別資訊": "Browser User Agent",
        "User Agent": "User Agent",
        "用於前端註冊 Push 訂閱": "Used for frontend Push subscription registration",
        "用於後端發送 Push 通知（請勿洩漏）": "Used for backend Push notifications (do not leak)",
        "用於取消交易時恢復書籍狀態（BR-14）": "Used to restore book status when cancelling a deal (BR-14)",
        
        # Appeal system
        "申訴": "Appeal",
        "申訴人": "Appellant",
        "申訴類型": "Appeal Type",
        "申訴詳情": "Appeal Details",
        "申訴已送出": "Appeal Submitted",
        "申訴狀態更新": "Appeal Status Updated",
        "申訴審核完成": "Appeal Reviewed",
        "審核中": "Under Review",
        "審核備註": "Review Notes",
        "審核時間": "Review Time",
        "審核結果": "Review Result",
        "審核者": "Reviewed By",
        "提交申訴": "Submit Appeal",
        "取消申訴": "Cancel Appeal",
        "您尚未提交任何申訴": "You haven't submitted any appeals yet",
        "尚無申訴紀錄": "No appeal records",
        "帳號停權申訴": "Account Suspension Appeal",
        "已通過": "Approved",
        "已駁回": "Rejected",
        "由 %(email)s 於 %(date)s 審核": "Reviewed by %(email)s on %(date)s",
        "否": "No",
        "是": "Yes",
        "是（使用者已遭停權）": "Yes (User is suspended)",
        
        # Books
        "書籍": "Book",
        "書籍簡介": "About This Book",
        "書籍詳情": "Book Details",
        "書名": "Title",
        "作者": "Author",
        "作者（正規化）": "Author (Normalized)",
        "出版社": "Publisher",
        "出版社（正規化）": "Publisher (Normalized)",
        "譯者": "Translator",
        "ISBN": "ISBN",
        "10 碼或 13 碼 ISBN": "10 or 13 digit ISBN",
        "分類": "Category",
        "全部分類": "All Categories",
        "小說": "Fiction",
        "科學": "Science",
        "科技": "Technology",
        "藝術": "Art",
        "文學": "Literature",
        "歷史": "History",
        "哲學": "Philosophy",
        "一般": "General",
        "未分類": "Uncategorized",
        "封面圖片": "Cover Image",
        "預設封面": "Default Cover",
        "書況描述": "Condition Description",
        "書況照片": "Condition Photos",
        "流通性": "Availability Type",
        "預設流通性": "Default Availability",
        "開放傳遞": "Open Transfer",
        "閱畢即還": "Return After Reading",
        "可移轉": "Transferable",
        "自由流通": "Free Circulation",
        "無借閱限制": "No Borrowing Limits",
        "暫不開放": "Not Available",
        "目前尚未上傳書況照片。": "No condition photos uploaded yet.",
        "狀態：": "Status:",
        "上架時間": "Listed Date",
        "上架閒置書籍": "List Idle Books",
        "上架第一本書": "List Your First Book",
        "新增分享書籍": "Add Shared Book",
        "新增書籍": "Add Book",
        "貢獻書籍": "Contribute Books",
        "分享書籍": "Share Book",
        "探索社群好書": "Discover Community Books",
        "開始探索書籍": "Start Exploring Books",
        "所有書籍": "All Books",
        "探索": "Explore",
        "搜尋 ISBN、書名、作者、出版社": "Search ISBN, title, author, publisher",
        "搜尋書籍": "Search Books",
        "查詢中…": "Searching…",
        "排序": "Sort",
        "排序鍵": "Sort Key",
        "空白時以顯示名稱小寫排序": "Lowercase display name used when blank",
        "顯示名稱": "Display Name",
        "名稱": "Name",
        "新視界": "New Horizon",
        "刪除": "Delete",
        "刪除書籍": "Delete Book",
        "確定要刪除這本書嗎？此操作無法復原。": "Are you sure you want to delete this book? This cannot be undone.",
        "確定要刪除這張照片嗎？": "Are you sure you want to delete this photo?",
        "編輯": "Edit",
        "編輯書籍資訊": "Edit Book Info",
        "儲存變更": "Save Changes",
        "查看書籍詳情": "View Book Details",
        "上傳照片": "Upload Photos",
        "照片": "Photos",
        "照片說明": "Photo Description",
        "上傳者": "Uploaded By",
        "分享失敗，請手動複製網址": "Share failed, please copy the URL manually",
        "已複製分享連結": "Share link copied",
        "我想分享這本書給你：%(title)s": "I want to share this book with you: %(title)s",
        
        # Official book
        "官方書目": "Official Bibliography",
        "書目作者關聯": "Book-Author Association",
        "預設流通性": "Default Availability",
        
        # Book set
        "套書": "Book Set",
        "套書名稱": "Book Set Name",
        "套書說明": "Description",
        "套書書籍 <span class=\"text-primary ml-1\">(%(count)s)</span>": "Books in Set <span class=\"text-primary ml-1\">(%(count)s)</span>",
        "建立套書": "Create Book Set",
        "管理套書": "Manage Book Sets",
        "我的套書": "My Book Sets",
        "此書籍為套書的一部分，借閱時需整套借出": "This book is part of a set; the entire set must be borrowed together",
        "所屬套書": "Part of Set",
        "最多借 %(max_books)s 本，最長 %(max_days)s 天": "Max %(max_books)s books, %(max_days)s days",
        "最大借閱天數": "Max Borrow Days",
        "最大持書數量": "Max Holding Count",
        
        # Wishlist
        "願望書車": "Wishlist",
        "願望清單": "Wishlist",
        "願望書籍已可借閱": "Wishlisted book is now available",
        "想看什麼書？": "What book are you looking for?",
        
        # Deal / Trading
        "交易": "Deal",
        "交易管理": "Deal Management",
        "交易詳情": "Deal Details",
        "交易申請": "Deal Request",
        "交易狀態": "Deal Status",
        "交易狀態進度": "Deal Status Progress",
        "交易類別": "Deal Type",
        "交易類型": "Deal Type",
        "交易夥伴": "Deal Partner",
        "交易書籍": "Deal Book",
        "交易留言": "Deal Messages",
        "交易紀錄": "Deal History",
        "交易結案": "Deal Closed",
        "交易結案（DONE）": "Deal Closed (DONE)",
        "交易被取消": "Deal Cancelled",
        "交易與信用統計": "Deal & Trust Statistics",
        "交易前書籍狀態": "Pre-Deal Book Status",
        "接受申請": "Accept Request",
        "婉拒": "Decline",
        "申請交易": "Request Deal",
        "申請借用": "Request Borrow",
        "申請傳遞": "Request Transfer",
        "申請回歸": "Request Return",
        "申請返還": "Request Return",
        "申請者": "Applicant",
        "申請資訊": "Application Info",
        "申請須知": "Application Guidelines",
        "申請取消": "Cancel Request",
        "取消借閱申請": "Cancel Borrow Request",
        "申請例外處理": "Request Exception",
        "例外狀況": "Exception",
        "例外處理": "Exception Handling",
        "例外處理 (EX)": "Exception Handling (EX)",
        "提交申請後，持書人將收到通知": "The book holder will be notified after you submit",
        "想跟對方說什麼？": "Any message for the other party?",
        "對方接受後，您可與持書人協商面交時間地點": "After acceptance, you can arrange meetup with the holder",
        "同一本書的多筆申請": "Multiple applications for the same book",
        "需要您處理的申請": "Pending Your Response",
        "進行中的請求": "Active Requests",
        "有 %(count)s 本書籍收到多筆申請，建議檢視後一併處理": "%(count)s books have multiple requests — review and process them together",
        "送出申請": "Submit Request",
        "新增申請": "New Request",
        "查看資料": "View Profile",
        "前往評價": "Go to Rating",
        "完成交易": "Complete Deal",
        "完成交易進度": "Deal Progress",
        "確認新增": "Confirm Add",
        "確認歸還／上架": "Confirm Return / Re-list",
        "確認歸還並重新上架": "Confirm Return & Re-list",
        "確認面交完成": "Confirm Meetup Complete",
        "面交完成": "Meetup Complete",
        "面交完成，請評價": "Meetup Complete — Please Rate",
        
        # Deal status
        "已請求": "Requested",
        "已回應": "Responded",
        "已面交": "Met Up",
        "已結案": "Closed",
        "已取消": "Cancelled",
        "已完成": "Completed",
        "已拒絕": "Rejected",
        "已提交": "Submitted",
        "已核准": "Approved",
        "已駁回": "Rejected",
        "已通過": "Approved",
        "已毀損": "Damaged",
        "已遺失": "Lost",
        "已逾期": "Overdue",
        "已讀": "Read",
        "待評價": "Pending Rating",
        "待回應": "Pending Response",
        "待審核": "Pending Review",
        "待面交": "Pending Meetup",
        "待對方回應": "Awaiting Response",
        "已被預約": "Reserved",
        "進行中": "In Progress",
        "未知": "Unknown",
        "面交地點": "Meetup Location",
        "面交時間": "Meetup Time",
        "預計借閱天數：%(days)s 天": "Expected borrow duration: %(days)s days",
        "天": "days",
        "本": "volumes",
        "最少 15 天，最多 90 天": "Minimum 15 days, maximum 90 days",
        "最少 7 天，最多 30 天": "Minimum 7 days, maximum 30 days",
        "取書地點": "Pickup Location",
        "可取書時間": "Available Pickup Times",
        "格式: [{\"weekday\": 1, \"start\": \"09:00\", \"end\": \"12:00\"}, ...]": "Format: [{\"weekday\": 1, \"start\": \"09:00\", \"end\": \"12:00\"}, ...]",
        
        # Deal types
        "借用交易": "Borrow Deal",
        "借用交易 (LN)": "Borrow Deal (LN)",
        "借閱中": "Currently Borrowed",
        "借閱天數": "Borrow Days",
        "借閱次數": "Borrow Count",
        "借閱書籍，閱畢後歸還給持書人": "Borrow a book, return to holder after reading",
        "傳遞交易": "Transfer Deal",
        "傳遞交易 (TF)": "Transfer Deal (TF)",
        "回歸交易": "Return Deal",
        "回歸交易 (RG)": "Return Deal (RG)",
        "返還交易": "Return Deal",
        "返還交易 (RS)": "Return Deal (RS)",
        "僅 LN/TF 類型交易需要": "Only required for LN/TF type deals",
        "若為套書交易，關聯至套書": "Link to book set if applicable",
        
        # Deal process
        "線下面交": "In-Person Meetup",
        "雙方在約定的時間地點碰面交書。確認書況無誤後，在平台上點擊「已面交」。": "Meet at the agreed time and place. Confirm book condition, then tap 'Met Up' on the platform.",
        "面交時請確認書況，並在系統中完成確認": "Check book condition at meetup, then confirm in the system",
        "面交時拍攝的照片關聯至交易": "Photos taken at meetup are linked to the deal",
        "留言溝通": "Send a Message",
        "發送訊息": "Send Message",
        "歷史留言紀錄": "Message History",
        "輸入訊息": "Type a message…",
        "訊息內容": "Message Content",
        "相關書籍": "Related Books",
        "相關交易": "Related Deals",
        
        # Rating
        "評價": "Rating",
        "給出評價": "Leave a Rating",
        "評價送出": "Rating Submitted",
        "評價爭議": "Rating Dispute",
        "評價者": "Rater",
        "被評價者": "Rated User",
        "評語": "Comment",
        "雙方完成互評": "Both Parties Have Rated",
        "雙向評價": "Two-Way Rating",
        "提示：待雙方評價完成後，主按鈕才會開啟": "Note: The main button will unlock after both parties have rated",
        "提示：即便對方尚未評價，主人仍可先點擊下方「確認歸還」。": "Note: You can confirm return even if the other party hasn't rated yet",
        "平均評價": "Average Rating",
        "友善評分": "Friendliness Score",
        "書況準確度評分": "Condition Accuracy Score",
        "準時評分": "Punctuality Score",
        
        # Overdue
        "逾期次數": "Overdue Count",
        "逾期爭議": "Overdue Dispute",
        "逾期處理": "Overdue Handling",
        "到期日": "Due Date",
        "書籍即將到期": "Book Due Soon",
        "書籍已逾期": "Book Overdue",
        "到期排程處理": "Scheduled Overdue Processing",
        "公開逾期名單": "Public Overdue List",
        "強制確認歸還": "Force Confirm Return",
        
        # Extension
        "延期申請紀錄": "Extension Request History",
        "延長申請": "Extension Request",
        "延長核准": "Extension Approved",
        "延長拒絕": "Extension Denied",
        "延長取消": "Extension Cancelled",
        "延長申請已核准": "Extension Approved",
        "延長申請已拒絕": "Extension Denied",
        "延長天數": "Extension Days",
        "可延長天數": "Allowable Extension Days",
        "最少 7 天，最多 30 天": "Minimum 7 days, maximum 30 days",
        
        # Exchange event
        "交換事件": "Exchange Event",
        "事件類型": "Event Type",
        "持有者變更": "Holder Changed",
        "歸還書籍給貢獻者": "Return Book to Owner",
        "主人確認歸還書籍": "Owner Confirmed Return",
        "貢獻者取回書籍": "Owner Retrieved Book",
        "強制確認歸還": "Force Confirm Return",
        "書籍傳遞給下一位讀者": "Book Passed to Next Reader",
        "確認歸還並重新上架": "Confirm Return & Re-list",
        "應返還": "Due for Return",
        "目前持有": "Currently Held By",
        "目前持有人：": "Current Holder:",
        "目前持有人": "Current Holder",
        "持有者": "Holder",
        "擁有者": "Owner",
        "擁有者：%(owner)s": "Owner: %(owner)s",
        
        # User profile
        "個人資料": "Profile",
        "個人": "Personal",
        "使用者資訊": "User Info",
        "用戶資料": "User Data",
        "用戶": "User",
        "成員": "Member",
        "電子信箱": "Email",
        "出生日期": "Date of Birth",
        "用於年齡驗證（需年滿 18 歲）": "For age verification (must be 18+)",
        "您的年齡未滿 18 歲，依法規限制無法註冊使用本服務": "You must be 18+ to register",
        "頭像": "Avatar",
        "%(nickname)s 的頭像": "%(nickname)s's Avatar",
        "%(nickname)s 的 Google 頭像": "%(nickname)s's Google Avatar",
        "Google 頭像": "Google Avatar",
        "未設定暱稱": "Nickname Not Set",
        "預設取書地點": "Default Meetup Location",
        "例如：台北市大安區": "e.g., Da'an District, Taipei",
        "聯絡信箱或網站 URL（mailto: 或 https://）": "Contact email or website URL (mailto: or https://)",
        "加入時間": "Member Since",
        "建立於 %(date)s": "Created %(date)s",
        "您目前持有的書籍": "Books You Currently Hold",
        "您貢獻的書籍": "Books You've Contributed",
        "我的貢獻": "My Contributions",
        "我的書架": "My Bookshelf",
        "我的申訴": "My Appeals",
        "貢獻者": "Contributor",
        "持書人": "Book Holder",
        "持書人頭像": "Holder Avatar",
        "寄件人": "Sender",
        "收件人": "Recipient",
        
        # UI elements
        "首頁": "Home",
        "探索": "Explore",
        "書架": "Bookshelf",
        "選單": "Menu",
        "主選單": "Main Menu",
        "關閉選單": "Close Menu",
        "返回": "Back",
        "返回首頁": "Back to Home",
        "返回交易列表": "Back to Deal List",
        "前往": "Go",
        "取消": "Cancel",
        "確認": "Confirm",
        "確定": "OK",
        "標題": "Title",
        "主體": "Body",
        "描述": "Description",
        "狀態": "Status",
        "狀態更新": "Status Updated",
        "附加資料": "Attachments",
        "證據文件": "Evidence Documents",
        "來源": "Source",
        "操作": "Actions",
        "下載我的資料": "Download My Data",
        "關於與幫助": "About & Help",
        "了解運作機制": "How It Works",
        "運作機制": "How It Works",
        
        # Welcome / Landing
        "Exbooks 共享書籍": "Exbooks — Community Book Sharing",
        "Exbooks 共享書籍 v1.0": "Exbooks v1.0",
        "Exbooks 共享書籍 - 讓好書自由流動": "Exbooks — Let Good Books Flow Freely",
        "Exbooks - 未來感共享體驗": "Exbooks — Futuristic Sharing Experience",
        "公益性質的去中心化書籍共享社群": "A non-profit, decentralized book sharing community",
        "為什麼選擇 Exbooks？": "Why Exbooks?",
        "打破傳統借閱限制，建立以信任為基礎的書籍共享生態系。": "Breaking traditional borrowing limits to build a trust-based book sharing ecosystem.",
        "簡單四個步驟，開啟你的書籍共享旅程": "Four simple steps to start your book sharing journey",
        "準備好開始您的閱讀旅程了嗎？": "Ready to start your reading journey?",
        "立即加入": "Join Now",
        "讓好書": "Let Good Books",
        "讓知識流動。": "Let Knowledge Flow.",
        "加入我們，讓閒置的書籍發揮最大價值，遇見更多同樣熱愛閱讀的朋友。": "Join us — give idle books new life and meet fellow book lovers.",
        "去中心化管理": "Decentralized Management",
        "雙軌流通模式": "Dual Circulation Model",
        "知識無界限": "Knowledge Without Borders",
        "新會員": "New Member",
        "新手": "Beginner",
        "新手任務": "Beginner Tasks",
        "新手暫無編輯權限": "Beginners cannot edit yet",
        "新手等級尚無編輯權限": "Beginner level has no edit permissions",
        "開發中": "Under Development",
        
        # Stats
        "出借次數": "Times Lent",
        "成功歸還次數": "Successful Returns",
        "活動統計": "Activity Stats",
        "摘要指標": "Summary Metrics",
        "共 ": "Total: ",
        " %(counter)s 本書籍": "%(counter)s books",
        "有 %(count)s 本書已逾期": "%(count)s books overdue",
        " %(count)s 筆": "%(count)s entries",
        "今日剩餘 <span id=\"remaining-exports\">--</span> 次": "Remaining today: <span id=\"remaining-exports\">--</span>",
        
        # Footer / status
        "您還沒有已完成的交易記錄": "No completed deals yet",
        "您還沒有待對方回應的交易申請": "No pending deal requests",
        "您還沒有建立任何套書": "No book sets created yet",
        "目前沒有待處理的交易": "No pending deals",
        "目前沒有待評價的交易": "No deals awaiting rating",
        "目前沒有約定面交的交易": "No scheduled meetups",
        "目前沒有資料": "No data available",
        "目前無法申請交易": "Cannot request a deal at this time",
        "等待收書方確認歸還或雙方先完成互評": "Awaiting the borrower to confirm return or both parties to rate each other",
        "尚未評價": "Not Yet Rated",
        "全部流通性": "All Availability",
        "接收者": "Receiver",
        "回應者": "Respondent",
        "回應者已評價": "Respondent Rated",
        "申請者已評價": "Applicant Rated",
        "申請者取消": "Cancelled by Applicant",
        "已回應": "Responded",
        "交易接受": "Deal Accepted",
        "交易婉拒": "Deal Declined",
        "交易已被回應": "Deal Has Been Responded To",
        
        # Error / misc
        "請修正以下錯誤：": "Please correct the following errors:",
        "請稍候": "Please wait…",
        "登出": "Log Out",
        "登入 / 註冊": "Log In / Register",
        "帳號已禁用": "Account Disabled",
        "錯誤": "Error",
        "發生錯誤": "An error occurred",
        "成功": "Success",
        "新增成功": "Added successfully",
        "更新成功": "Updated successfully",
        "刪除成功": "Deleted successfully",
        "以電子郵件寄送": "Send via Email",
        "複製分享網址": "Copy Share URL",
        "電腦": "Computer",
        "手機": "Mobile",
        "平板": "Tablet",
        "徽章圖標": "Badge Icon",
        "CSS class 或圖片路徑": "CSS class or image path",
        "空白": "Blank",
        "（可選）": "(Optional)",
        "（必填）": "(Required)",
        "無資料": "No Data",
        "載入中…": "Loading…",
        "處理中…": "Processing…",
        
        # Messages/notifications
        "交易抱怨": "Deal Complaint",
        "交易訊息": "Deal Message",
        "系統": "System",
        "管理員": "Admin",
        "自動": "Auto",
        "尚未設定": "Not Set",
        "未指定": "Not Specified",
        "無": "None",
        
        # Email verification
        "我們已寄出一封確認信。請至您的電子信箱點擊連結以完成註冊流程。": "We've sent a confirmation email. Click the link to complete your registration.",
        "確認電子信箱": "Confirm Email",
        "重寄確認信": "Resend Confirmation",
        
        # Alert
        "確認信箱": "Email Confirmation",
        "密碼重設": "Password Reset",
        "安全性": "Security",
        
        # Search result page info
        "搜尋結果": "Search Results",
        "找到 %(count)s 筆結果": "Found %(count)s results",
        "顯示 %(start)s - %(end)s，共 %(total)s 筆": "Showing %(start)s–%(end)s of %(total)s",
      
        # Deal list
        "對 %(nickname)s 的評價": "Rating for %(nickname)s",
        "關於 %(nickname)s 的評價": "Ratings about %(nickname)s",
        "來自 %(nickname)s 的評價": "Rating from %(nickname)s",
        
        # Template titles
        "Exbooks - %(title)s": "Exbooks — %(title)s",
        "%(name)s - Exbooks": "%(name)s — Exbooks",
        "Exbooks - 交易管理": "Exbooks — Deal Management",
        "Exbooks - 交易詳情": "Exbooks — Deal Details",
        "Exbooks - 新增書籍": "Exbooks — Add Book",
        "Exbooks - 編輯書籍": "Exbooks — Edit Book",
        "Exbooks - 所有書籍": "Exbooks — All Books",
        "Exbooks - 個人資料": "Exbooks — Profile",
        "Exbooks - 編輯個人資料": "Exbooks — Edit Profile",
        "Exbooks - 我的書架": "Exbooks — My Bookshelf",
        "Exbooks - 我的申訴": "Exbooks — My Appeals",
        "Exbooks - 申訴詳情": "Exbooks — Appeal Details",
        "Exbooks - 申請交易": "Exbooks — Request Deal",
        "Exbooks - 願望書車": "Exbooks — Wishlist",
        "我的套書 - Exbooks": "My Book Sets — Exbooks",
        
        # app strings
        "等待中": "Pending",
        "可借用": "Available for Borrow",
        "可預約": "Available for Reservation",
        "已預約": "Reserved",
        "不可借用": "Not Available",
        "下載中": "Downloading",
        "下載完成": "Download Complete",
        "上傳中": "Uploading",
        "上傳完成": "Upload Complete",
        "備份": "Backup",
        "還原": "Restore",
        "匯出": "Export",
        "匯入": "Import",
        "是否停權中": "Is Suspended",
        "停權結束時間": "Suspension End Time",
        "暫時停權的結束時間，null 表示永久停權": "End time of temporary suspension (null = permanent)",
        "停權原因": "Suspension Reason",
        "已損毀": "Damaged",
        "競價替代取消（BR-15）": "Bid Replacement Cancellation (BR-15)",
        "申請狀態": "Application Status",
        "是否啟用": "Enabled",
        "繁體中文": "Traditional Chinese",
        "請確認 <span class=\"font-semibold text-slate-900\">%(email)s</span> ": "Please confirm <span class=\"font-semibold text-slate-900\">%(email)s</span> ",
        "此確認連結已過期或無效。請 <a href=\"%(email_url)s\" class=\"text-primary ": "This confirmation link has expired or is invalid. Please <a href=\"%(email_url)s\" class=\"text-primary ",
        "編輯個人資料": "Edit Profile",
        "%(counter)s 本書籍": "%(counter)s books",
        " 本": " volumes",
        " 筆": " entries",
        "沒有實體圖書館，每一位社員都是圖書管理員。拿出你的閒置藏書，與熱愛閱讀的朋友交換，建立互信的閱讀社群。": "No physical library — every member is a librarian. Share idle books with fellow readers and build a trusted reading community.",
        "不再依賴中央圖書館，書籍由擁有者自行保管或在社群間流傳，實現真正的共享經濟。": "No central library — books are kept by owners or circulate within the community, enabling true sharing economy.",
        "自由設定書籍為「開放傳遞」讓書持續漂流，或「閱畢即還」確保愛書回到身邊。": "Set books to 'Open Transfer' for ongoing circulation or 'Return After Reading' to ensure they come back.",
        "面交後雙方互評誠信、準時與書況，累積社群信用，確保每一次借閱都令人安心。": "Rate each other on trust, punctuality, and book condition to build community credit for worry-free borrowing.",
        "輸入 ISBN 或書名，設定流通方式（開放傳遞/閱畢即還）與可面交時間地點，將愛書分享給社群。": "Enter ISBN or title, set availability type and meetup details, then share your book with the community.",
        "探索與申請": "Discover & Request",
        "在平台上尋找感興趣的書籍，發送借閱申請並與書籍目前的持有者確認面交細節。": "Find books you love, send a borrow request, and arrange a meetup with the current holder.",
        "針對此次交易的友善度、準時度與書況準確度給予評價，共同維護高品質的共享環境。": "Rate friendliness, punctuality, and condition accuracy to maintain a high-quality sharing environment.",
        "書籍遺失、損毀或尋獲": "Book Lost, Damaged, or Found",
        "確認面交完成？\\\\n\\\\n確認後交易將進入「已面交」狀態，雙方可以開始互評。": "Confirm meetup complete?\\n\\nThe deal will enter 'Met Up' status and both parties can start rating.",
        "注意：雙方尚未完成互評。如果您已收到書籍，可以強制確認歸還，但這將無法獲得完整的信用積分。確定要繼續嗎？": "Note: Both parties haven't rated yet. You can force-confirm return, but won't receive full trust score. Continue?",
        "%(count)s 筆": "%(count)s entries",
        "可信": "Trustworthy",
        "優良": "Excellent",
    }
    
    if text in translations:
        return translations[text]
    
    # Fallback: if the string has no Chinese characters, return as-is
    if not re.search(r'[\u4e00-\u9fff]', text):
        return text
    
    # Otherwise, generate a basic English version
    return f"[TBD] {text}"


def fill_english():
    """Translate Chinese msgid to English msgstr."""
    po = polib.pofile(EN_PO)
    count = 0
    skipped = 0
    for entry in po:
        if not entry.msgid:
            continue
        if entry.msgstr:
            skipped += 1
            continue
        translation = translate_chinese_to_english(entry.msgid)
        entry.msgstr = translation
        count += 1
    po.save()
    print(f"en: translated {count} strings ({skipped} already had translations)")


if __name__ == "__main__":
    fill_zh_hant()
    fill_english()
