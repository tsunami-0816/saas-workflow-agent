import bcrypt

h = b"$2a$10$.dnmagwYHZ4ERMqsOuOkveV3eKom51eNrstxrDmtq3dZ36aT46oNK"
for pw in [b"Swa@123456", b"swa@123456", b"Swa123456", b"admin123", b"123456"]:
    try:
        print(pw.decode(), "=>", bcrypt.checkpw(pw, h))
    except Exception as e:
        print(pw.decode(), "=> ERROR", e)
# 生成一个确定正确的新哈希备用
print("new hash for Swa@123456:", bcrypt.hashpw(b"Swa@123456", bcrypt.gensalt(10, prefix=b"2a")).decode())
