@startuml use_case
 
title "<color #1A6><size 15>Exbooks 共享書籍</size></color>\n<color #16A><size 18>Use Case Diagram 用例圖</size></color>\n<color grey>v2.7.0 @2026-07-01</color>\n"
 
left to right direction
 
actor Timer as "  系統計時器\nSystem Timer" #9C3
actor SysAdmin as "系統管理員\n   DBA" #F66
actor NonMember as "非會員"
actor Member as "  會員\nMember" #B83
actor Reader as "  讀者\nReader" #BFB
actor Keeper as "書籍持有者\n  Keeper" #9EF
actor Owner as "書籍貢獻者\n  Owner" #FBD
 
rectangle "一般功能" {
  usecase OAM as "系統維運"
 
  usecase ProcessBookDue as "處理\n書籍借閱到期\nDue" #9C3
  usecase MailNotice as "發通知信給：\n1.持有者\n2.願望書車的讀者"
 
  usecase ProcessDeal as "處理交易內容\nDeal" #C93
  usecase ChgDealStatus as "變更交易狀態"
  usecase ChgBookKeeper as "變更書籍持有人"
  usecase PhotoUpload as "拍攝書況照片\n上傳"
  usecase RateUser as "評價\n交易對象"
  usecase ChgBookStatus as "變更書籍狀態為：\n「可移轉」或\n「應返還」"
 
  usecase Regist as "註冊會員"
  usecase EditProfile as "編輯用戶資料"
  usecase SearchBook as "查詢書籍\nSearch Book" #FEE
  usecase QueryCredit as "查詢信用評價\nQuery Credit" #FEE
  usecase WishList as "願望書車\nWish List" #6d6464
  usecase ExtendLoan as "申請延長借閱"
  usecase ApproveExtend as "核准延長借閱"
  usecase DeclineDeal as "拒絕交易申請"
  usecase CancelRequest as "取消申請\nCancel Request" #FAA
  usecase SelectApplicant as "選擇接受\n申請者" #FEE
  usecase Negotiate as "交易留言\n協商面交細節" #FEE
 
  usecase Transfer as "傳遞交易\nTransfer Deal\n預約、面交" #8FE
  usecase Import as "申請「傳遞交易」\n~ 轉入 Import" #CFE
  usecase Export as "回應「傳遞交易」\n~ 轉出 Export" #CFE
 
  usecase Loan as "借用交易\nLoan Deal\n預約、面交" #AFA
  usecase Borrow as "申請「借用交易」\n~ 借入 Borrow" #DFD
  usecase Lend as "回應「借用交易」\n~ 借出 Lend" #DFD
 
  usecase Restore as "返還交易\nRestore Deal\n預約、面交" #FF6
  usecase Return as "申請「返還交易」\n~ 歸還 Return" #FFB
  usecase Retrieve as "回應「返還交易」\n~ 取回 Retrieve" #FFB
 
  usecase Regress as "回歸交易\nRegress Deal\n預約、面交" #DBE
  usecase Withdraw as "申請「回歸交易」\n~ 撤回 Withdraw" #EDF
  usecase Revert as "回應「回歸交易」\n~ 交回 Revert" #EDF
 
  usecase Except as "例外狀況\nExcept Deal\n遺失、損毀" #F94
  usecase Declare as "申請「例外狀況」\n~ 宣告 Declare" #FCB
  usecase Resolve as "回應「例外狀況」\n~ 處置 Resolve" #FCB
 
  usecase Provide as "貢獻書籍\nProvide" #FBD
  usecase AIChatBot as "AI 書本推薦\n與問答" #9CF
  usecase WebPushSubscribe as "訂閱 Web Push\n推播通知" #9CF
  usecase WebPushUnsubscribe as "取消訂閱\nWeb Push" #9CF
  usecase ExportUserData as "匯出個人資料\nExport Data" #9CF
  usecase ConfirmReturn as "確認歸還\n強制歸還" #FAA
}
 
Member <|-- Reader
Member <|-- Keeper
Member <|-- Owner 
 
NonMember --> Regist
NonMember --> SearchBook
 
Member --> EditProfile
Member --> SearchBook
Member --> QueryCredit
Member --> RateUser
Member --> AIChatBot
Member --> WebPushSubscribe
Member --> WebPushUnsubscribe
Member --> ExportUserData
 
Timer --> ProcessBookDue
SysAdmin --> OAM
 
Reader --> WishList
Reader --> Import
Reader --> Borrow
Reader --> Return
Reader --> ExtendLoan
Reader --> Negotiate
Reader --> CancelRequest
 
Keeper --> Export
Keeper --> Revert
Keeper --> Declare
Keeper --> DeclineDeal
Keeper --> SelectApplicant
Keeper --> Negotiate
Keeper --> ApproveExtend
Keeper --> CancelRequest
 
Owner --> Lend
Owner --> Retrieve
Owner --> Withdraw
Owner --> Resolve
Owner --> Provide
Owner --> DeclineDeal
Owner --> SelectApplicant
Owner --> Negotiate
Owner --> ApproveExtend
Owner --> CancelRequest
Owner --> ConfirmReturn
 
ExtendLoan --> ApproveExtend : <<extend>>
 
SelectApplicant --> Export : <<extend>>
SelectApplicant --> Lend : <<extend>>
 
Import --> Transfer : <<extend>>
Export --> Transfer : <<extend>>
Borrow --> Loan : <<extend>>
Lend --> Loan : <<extend>>
Retrieve --> Restore : <<extend>>
Return --> Restore : <<extend>>
Withdraw --> Regress : <<extend>>
Revert --> Regress : <<extend>>
Declare --> Except : <<extend>>
Resolve --> Except : <<extend>>
 
Transfer --> ProcessDeal : <<extend>>
Loan --> ProcessDeal : <<extend>>
Restore --> ProcessDeal : <<extend>>
Regress --> ProcessDeal : <<extend>>
Except --> ProcessDeal : <<extend>>
CancelRequest --> ProcessDeal : <<extend>>
 
ProcessBookDue --> ChgBookStatus : <<include>>
ProcessBookDue --> MailNotice : <<include>>
ProcessDeal --> MailNotice : <<include>>
ProcessDeal --> ChgBookStatus : <<include>>
ProcessDeal --> ChgDealStatus : <<include>>
ProcessDeal --> ChgBookKeeper : <<include>>
ProcessDeal --> PhotoUpload : <<include>>
ProcessDeal --> RateUser : <<include>>
ProcessDeal --> Negotiate : <<extend>>
 
@enduml