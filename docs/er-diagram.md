## ER Diagram

## Accounts Detail

```mermaid
erDiagram
    User ||--|| UserProfile : "擴展"
    User ||--o{ Violation : "違規"
    User ||--o{ Appeal : "申訴"
    User ||--o{ TrustScoreLedger : "信用稽核"

    User {
        INT id PK
    }

    UserProfile {
        UUID id PK
        INT user_id FK
        VARCHAR nickname
        DATE birth_date
        ENUM default_transferability
        VARCHAR default_location
        JSON available_schedule
        VARCHAR avatar
        INT trust_score
        INT successful_returns
        INT overdue_count
        BOOLEAN is_suspended
        DATETIME suspension_end_date
        TEXT suspension_reason
        DATETIME trust_level_protected_since
        BOOLEAN push_enabled
        BOOLEAN email_notifications_enabled
        DATETIME created_at
        DATETIME updated_at
    }

    Violation {
        UUID id PK
        INT user_id FK
        ENUM action_type
        ENUM severity
        ENUM violation_type
        TEXT description
        INT suspension_days
        BOOLEAN is_active
        INT created_by_id FK
        INT related_appeal_id FK "ref: Appeals"
        DATETIME lifted_at
        INT lifted_by_id FK
        DATETIME created_at
        DATETIME updated_at
    }

    Appeal {
        UUID id PK
        INT user_id FK
        ENUM appeal_type
        VARCHAR title
        TEXT description
        VARCHAR evidence
        ENUM status
        TEXT resolution_notes
        INT resolved_by_id FK
        DATETIME resolved_at
        DATETIME created_at
        DATETIME updated_at
    }

    TrustLevelConfig {
        INT level PK
        VARCHAR group_name
        VARCHAR display_name
        INT min_score
        INT max_books
        INT max_days
        INT demotion_protection_weeks
        VARCHAR badge_icon
    }

    TrustScoreLedger {
        UUID id PK
        INT user_id FK
        INT trust_score
        INT trust_level
        VARCHAR formula_version
        ENUM source
        VARCHAR trace_id
        JSON payload
        DATETIME created_at
    }
```

## Books Detail

```mermaid
erDiagram
    User ||--o{ SharedBook : "貢獻 (owner)"
    User ||--o{ SharedBook : "持有 (keeper)"
    User ||--o{ BookSet : "建立"
    User ||--o{ BookPhoto : "上傳"
    User ||--o{ WishListItem : "收藏"

    OfficialBook ||--o{ SharedBook : "實例化"
    OfficialBook ||--o{ WishListItem : "被收藏"
    OfficialBook }o--|| Publisher : "出版社（正規化）"
    OfficialBook ||--o{ OfficialBookAuthor : "作者關聯"
    Author ||--o{ OfficialBookAuthor : "作品關聯"

    BookSet ||--o{ SharedBook : "包含"
    SharedBook ||--o{ BookPhoto : "書況紀錄"

    User {
        INT id PK "ref: Accounts"
    }

    OfficialBook {
        UUID id PK
        VARCHAR isbn UK
        VARCHAR title
        VARCHAR author
        VARCHAR publisher
        ENUM category
        VARCHAR cover_image
        TEXT description
        INT publisher_ref_id FK "ref: Publisher"
        DATETIME created_at
        DATETIME updated_at
    }

    Author {
        UUID id PK
        VARCHAR display_name UK
        VARCHAR sort_key
        DATETIME created_at
        DATETIME updated_at
    }

    Publisher {
        UUID id PK
        VARCHAR name UK
        DATETIME created_at
        DATETIME updated_at
    }

    OfficialBookAuthor {
        UUID id PK
        INT official_book_id FK
        INT author_id FK
        ENUM role
        INT sort_order
        DATETIME created_at
    }

    BookSet {
        UUID id PK
        INT owner_id FK
        VARCHAR name
        TEXT description
        DATETIME created_at
        DATETIME updated_at
    }

    SharedBook {
        UUID id PK
        INT official_book_id FK
        INT owner_id FK
        INT keeper_id FK
        INT book_set_id FK
        ENUM transferability
        ENUM status
        TEXT condition_description
        INT loan_duration_days
        INT extend_duration_days
        INT min_trust_level
        DATETIME listed_at
        DATETIME created_at
        DATETIME updated_at
    }

    BookPhoto {
        UUID id PK
        INT shared_book_id FK
        INT deal_id FK "ref: Deals"
        INT uploader_id FK
        VARCHAR photo
        VARCHAR caption
        DATETIME created_at
    }

    WishListItem {
        UUID id PK
        INT user_id FK
        INT official_book_id FK
        DATETIME created_at
    }
```

## Deals Detail

```mermaid
erDiagram
    User ||--o{ Deal : "申請 (applicant)"
    User ||--o{ Deal : "回應 (responder)"
    User ||--o{ DealMessage : "發送"
    User ||--o{ Rating : "評價 (rater)"
    User ||--o{ Rating : "被評 (ratee)"
    User ||--o{ LoanExtension : "申請延長"
    User ||--o{ Notification : "接收"
    User ||--o{ ExchangeEvent : "操作"
    User ||--o{ PushSubscription : "Push 訂閱"

    SharedBook ||--o{ Deal : "交易標的"
    SharedBook ||--o{ ExchangeEvent : "稽核事件"

    Deal ||--o{ DealMessage : "協商"
    Deal ||--o{ Rating : "產生評價"
    Deal ||--o{ LoanExtension : "延長申請"
    Deal ||--o{ Notification : "觸發通知"
    Deal ||--o{ ExchangeEvent : "稽核事件"

    User {
        INT id PK "ref: Accounts"
    }

    SharedBook {
        UUID id PK "ref: Books"
        ENUM status
    }

    Deal {
        UUID id PK
        INT shared_book_id FK
        INT book_set_id FK
        ENUM deal_type
        ENUM status
        VARCHAR previous_book_status
        INT applicant_id FK
        INT responder_id FK
        VARCHAR meeting_location
        DATETIME meeting_time
        DATE due_date
        BOOLEAN applicant_rated
        BOOLEAN responder_rated
        DATETIME created_at
        DATETIME updated_at
    }

    DealMessage {
        UUID id PK
        INT deal_id FK
        INT sender_id FK
        TEXT content
        DATETIME created_at
    }

    Rating {
        UUID id PK
        INT deal_id FK
        INT rater_id FK
        INT ratee_id FK
        TINYINT friendliness_score
        TINYINT punctuality_score
        TINYINT accuracy_score
        TEXT comment
        DATETIME created_at
    }

    LoanExtension {
        UUID id PK
        INT deal_id FK
        INT requested_by_id FK
        INT approved_by_id FK
        INT extra_days
        ENUM status
        DATETIME created_at
        DATETIME updated_at
    }

    Notification {
        UUID id PK
        INT recipient_id FK
        INT deal_id FK
        INT shared_book_id FK
        ENUM notification_type
        VARCHAR title
        TEXT message
        BOOLEAN is_read
        DATETIME created_at
    }

    ExchangeEvent {
        UUID id PK
        INT shared_book_id FK
        INT deal_id FK
        ENUM event_type
        INT actor_id FK
        VARCHAR trace_id
        JSON metadata
        DATETIME created_at
    }

    PushSubscription {
        UUID id PK
        INT user_id FK
        VARCHAR endpoint UK
        VARCHAR p256dh
        VARCHAR auth
        VARCHAR user_agent
        BOOLEAN is_active
        DATETIME created_at
    }
```
