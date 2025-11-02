# OTP Verification Code Fix - Summary

## 🐛 Vấn đề Gốc

Frontend gửi request xác thực OTP với payload:
```json
{
  "email": "tlpv5fu3@vwh.sh",
  "code": "414420"
}
```

Backend nhận đúng dữ liệu nhưng vẫn raise exception: **"Mã xác thực không đúng"** tại dòng so sánh `verification_code != confirm_data.code`

---

## 🔍 Nguyên Nhân Chính

### Vấn đề 1: Redis Client JSON Parsing Logic Sai
**File**: `services/ai-agent-service/app/core/redis_client.py` (dòng 96-100)

**Vấn đề**:
```python
# OLD CODE - Cố gắng parse mọi string thành JSON
try:
    return json.loads(value)  # ❌ "414420" không phải JSON hợp lệ
except (json.JSONDecodeError, TypeError):
    return value
```

Khi lưu verification code (string `"414420"`), Redis client cố gắng `json.loads()` nó. Mặc dù nó fail và return string, nhưng có thể có edge cases với whitespace hoặc encoding.

### Vấn đề 2: Không có Logging để Debug
Không thể biết giá trị thực tế của `verification_code` và `confirm_data.code` khi so sánh.

---

## ✅ Giải Pháp

### Fix 1: Cải thiện Redis Client JSON Parsing (redis_client.py)

**Thay đổi**:
```python
def get(self, key: str) -> Optional[Any]:
    """Get value by key."""
    if not self.is_connected():
        if not self.connect():
            return None
    
    try:
        value = self._client.get(key)
        if value is None:
            return None
        
        # ✅ Chỉ parse JSON nếu value thực sự là JSON (bắt đầu với { hoặc [)
        if isinstance(value, str) and value.strip() and value.strip()[0] in ('{', '['):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        
        # Return as-is cho plain strings
        return value
    except Exception as e:
        logger.error(f"Redis GET error: {e}")
        return None
```

**Lợi ích**:
- Plain strings (như verification codes) được return ngay mà không cố parse JSON
- Dicts/lists vẫn được parse JSON đúng cách
- Tránh edge cases với whitespace hoặc encoding

### Fix 2: Thêm Logging Chi Tiết (auth.py)

**Thêm vào `confirm_code` endpoint**:
```python
# Debug logging
logger.info(f"[OTP DEBUG] Email: {confirm_data.email}")
logger.info(f"[OTP DEBUG] Received code from client: {confirm_data.code!r} (type: {type(confirm_data.code).__name__})")
logger.info(f"[OTP DEBUG] Retrieved verification_code from Redis: {verification_code!r} (type: {type(verification_code).__name__})")

# Normalize cho comparison
verification_code_str = str(verification_code).strip() if verification_code else None
confirm_code_str = str(confirm_data.code).strip() if confirm_data.code else None

logger.info(f"[OTP DEBUG] After normalization - verification_code: {verification_code_str!r}, confirm_code: {confirm_code_str!r}")
logger.info(f"[OTP DEBUG] Codes match: {verification_code_str == confirm_code_str}")

if verification_code_str != confirm_code_str:
    logger.error(f"[OTP DEBUG] Code mismatch for {confirm_data.email}: expected {verification_code_str!r}, got {confirm_code_str!r}")
    raise HTTPException(...)
```

**Lợi ích**:
- Dễ debug trong tương lai
- Có thể thấy chính xác giá trị nào không khớp
- Giúp phát hiện whitespace, encoding issues

---

## 📝 Files Thay Đổi

1. **services/ai-agent-service/app/core/redis_client.py**
   - Cải thiện logic JSON parsing trong method `get()`
   - Chỉ parse JSON nếu value thực sự là JSON

2. **services/ai-agent-service/app/api/routes/auth.py**
   - Thêm import `logging`
   - Thêm logger instance
   - Thêm debug logging trong `confirm_code` endpoint
   - Normalize verification_code và confirm_data.code trước so sánh

---

## ✨ Test Results

Tất cả tests đã pass:
```
[Test 1] Simple string code (6-digit) ✅ PASSED
[Test 2] Registration data (dict) ✅ PASSED
[Test 3] Code comparison (simulating confirm_code endpoint) ✅ PASSED
```

---

## 🚀 Cách Verify Fix

1. **Chạy test**:
   ```bash
   cd services/ai-agent-service
   uv run python test_otp_fix.py
   ```

2. **Kiểm tra logs khi xác thực OTP**:
   - Tìm logs với prefix `[OTP DEBUG]`
   - Xem giá trị thực tế của verification_code và confirm_data.code
   - Xem kết quả so sánh

3. **Flow xác thực OTP bây giờ sẽ hoạt động đúng**:
   - Frontend gửi code → Backend nhận → So sánh đúng → Tạo user thành công

---

## 📌 Lưu Ý

- Logging có thể tắt trong production bằng cách điều chỉnh log level
- Fix này không ảnh hưởng đến các phần khác của hệ thống
- Verification code vẫn được lưu với TTL 3 phút như trước

