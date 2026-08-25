CREATE TABLE email_drafts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    msg_id VARCHAR(100) UNIQUE NOT NULL,
    sender VARCHAR(200) NOT NULL,
    subject VARCHAR(500),
    body TEXT,
    reply TEXT,
    created_at DATETIME DEFAULT NOW()
);
