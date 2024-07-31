INSERT INTO "user" (username, email, password, role)
VALUES ('admin', 'leohenryroberts+admin@gmail.com', '$2b$12$K2Gh26rUMwymWeHRzX3XB.ll/h0VPDTfnT17gWORCCe6jLlJL/3VO', 'admin')
ON CONFLICT (username) DO NOTHING;
