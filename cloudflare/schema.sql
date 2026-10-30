-- IMD DAWSA AI Cloudflare D1 baseline schema
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
 password_hash TEXT NOT NULL, display_name TEXT NOT NULL, handle TEXT UNIQUE,
 bio TEXT NOT NULL DEFAULT '', email_verified INTEGER NOT NULL DEFAULT 0,
 totp_secret_enc TEXT, totp_enabled INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS conversations (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
 user_message TEXT NOT NULL, assistant_message TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS posts (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 content TEXT NOT NULL, visibility TEXT NOT NULL DEFAULT 'public'
 CHECK (visibility IN ('public','followers','private')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS follows (
 follower_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 following_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY (follower_id, following_id), CHECK (follower_id <> following_id)
);
CREATE TABLE IF NOT EXISTS post_likes (
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id,post_id)
);
CREATE TABLE IF NOT EXISTS post_comments (
 id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, content TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS direct_messages (
 id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 receiver_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, content TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, CHECK(sender_id <> receiver_id)
);
CREATE TABLE IF NOT EXISTS marketplace_listings (
 id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', category TEXT NOT NULL DEFAULT 'general',
 price_amount REAL, currency TEXT NOT NULL DEFAULT 'USD',
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS marketplace_enquiries (
 id INTEGER PRIMARY KEY AUTOINCREMENT, listing_id INTEGER NOT NULL REFERENCES marketplace_listings(id) ON DELETE CASCADE,
 buyer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, message TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS notifications (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL, kind TEXT NOT NULL,
 object_type TEXT, object_id INTEGER, message TEXT NOT NULL, read_at TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, actor_user_id INTEGER, event_type TEXT NOT NULL,
 resource_type TEXT, resource_id TEXT, metadata_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id_id ON conversations(user_id,id DESC);
CREATE INDEX IF NOT EXISTS idx_posts_created_id ON posts(id DESC);
CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_pair ON direct_messages(sender_id,receiver_id,id DESC);
CREATE INDEX IF NOT EXISTS idx_marketplace_active ON marketplace_listings(status,id DESC);
CREATE INDEX IF NOT EXISTS idx_marketplace_seller ON marketplace_listings(seller_id,id DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_user_created ON notifications(user_id,id DESC);
