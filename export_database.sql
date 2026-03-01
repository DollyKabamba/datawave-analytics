BEGIN TRANSACTION;
CREATE TABLE contacts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT, email TEXT, subject TEXT, message TEXT,
            is_read    INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
CREATE TABLE search_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            query      TEXT,
            results    INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
CREATE TABLE users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            first_name TEXT DEFAULT '',
            last_name  TEXT DEFAULT '',
            email      TEXT DEFAULT '',
            gender     TEXT DEFAULT '',
            role       TEXT DEFAULT 'viewer',
            photo      TEXT DEFAULT 'default.png',
            is_active  INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
INSERT INTO "users" VALUES(1,'admin','297f8d80a87d6b675883e3bc117e7a5a897fcdeb41c9cf0f1b7d949ef7eb6d64','Admin','Principal','admin@ensea.edu.ci','M','admin','default.png',1,'2026-02-27 12:48:08');
INSERT INTO "users" VALUES(2,'manager','f3cdf766bd8256fded84ed1590ab9bbc192ee1e930bd86b450905dfa09d31105','Marie','Manager','manager@ensea.edu.ci','F','manager','default.png',1,'2026-02-27 12:48:08');
INSERT INTO "users" VALUES(3,'analyst','345982ba4e71cf6789b88de67e9b5f769ff011065010a273bae02fee9ccead97','Adjoua','Analyst','analyst@ensea.edu.ci','F','analyst','default.png',1,'2026-02-27 12:48:08');
INSERT INTO "users" VALUES(4,'viewer','16a6746ed035d9b663c14e17b003df87a475237ac1a1b7806aba0144d8065f69','Jean','Viewer','viewer@ensea.edu.ci','M','viewer','default.png',1,'2026-02-27 12:48:08');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('users',4);
COMMIT;
