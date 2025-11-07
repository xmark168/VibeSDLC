# Cập nhật API User để bao gồm GitHub Installation ID

## Tổng quan

Đã cập nhật các API response schemas và route handlers trong `services/ai-agent-service/app/api/routes/users.py` để bao gồm thông tin `installation_id` từ GitHub installation được liên kết với user.

## Thay đổi chi tiết

### 1. Schema Update (`services/ai-agent-service/app/schemas.py`)

**Trước:**
```python
class UserPublic(SQLModel):
    id: UUID
    full_name: str
    email: EmailStr
    role: Role
```

**Sau:**
```python
class UserPublic(SQLModel):
    id: UUID
    full_name: str
    email: EmailStr
    role: Role
    github_installation_id: Optional[int] = None  # GitHub installation_id from linked installation
```

### 2. Helper Function (`services/ai-agent-service/app/api/routes/users.py`)

Đã thêm helper function `user_to_public()` để convert User model sang UserPublic schema:

```python
def user_to_public(user: User) -> UserPublic:
    """
    Convert User model to UserPublic schema with GitHub installation data.
    
    Args:
        user: User model instance (should have github_installations loaded)
    
    Returns:
        UserPublic schema with github_installation_id populated
    """
    github_installation_id = None
    if user.github_installations and len(user.github_installations) > 0:
        # Get the first (primary) installation's installation_id
        github_installation_id = user.github_installations[0].installation_id
    
    return UserPublic(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        github_installation_id=github_installation_id,
    )
```

### 3. Route Handlers Update

Đã cập nhật tất cả các route handlers để:
1. **Eager load** GitHub installation data bằng `selectinload()`
2. Sử dụng `user_to_public()` để convert sang response schema

#### Routes đã cập nhật:

1. **GET `/api/v1/users/`** - List all users (admin only)
   - Sử dụng `selectinload(User.github_installations)` để eager load
   - Convert list users sang UserPublic với `user_to_public()`

2. **POST `/api/v1/users/`** - Create new user (admin only)
   - Refresh user với `attribute_names=["github_installations"]`
   - Return `user_to_public(user)`

3. **PATCH `/api/v1/users/me`** - Update current user
   - Refresh với GitHub installations
   - Return converted UserPublic

4. **GET `/api/v1/users/me`** - Get current user
   - Refresh để load GitHub installations
   - Return với installation_id

5. **POST `/api/v1/users/signup`** - Register new user
   - Refresh và return với GitHub data

6. **GET `/api/v1/users/{user_id}`** - Get user by ID
   - Refresh và return với GitHub data
   - Improved authorization check

7. **PATCH `/api/v1/users/{user_id}`** - Update user (admin only)
   - Refresh và return với GitHub data

## Database Relationship

Model `User` có relationship one-to-many với `GitHubInstallation`:

```python
# User model
github_installations: list["GitHubInstallation"] = Relationship(
    back_populates="user", 
    sa_relationship_kwargs={"cascade": "all, delete-orphan"}
)

# GitHubInstallation model
installation_id: int = Field(unique=True, index=True, nullable=False)
user_id: UUID | None = Field(default=None, foreign_key="users.id", nullable=True, ondelete="CASCADE")
```

## Eager Loading Strategy

Sử dụng SQLAlchemy's `selectinload()` để tránh N+1 query problem:

```python
from sqlalchemy.orm import selectinload

# Trong query
statement = select(User).options(selectinload(User.github_installations))
```

Hoặc sử dụng `session.refresh()` với `attribute_names`:

```python
session.refresh(user, attribute_names=["github_installations"])
```

## API Response Example

**Request:**
```bash
GET /api/v1/users/me
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "full_name": "John Doe",
  "email": "john@example.com",
  "role": "user",
  "github_installation_id": 12345678
}
```

Nếu user chưa link GitHub installation:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "full_name": "John Doe",
  "email": "john@example.com",
  "role": "user",
  "github_installation_id": null
}
```

## Frontend Integration

Sau khi regenerate API client, frontend có thể access `github_installation_id`:

```typescript
import { UsersService } from "@/client"

// Get current user
const user = await UsersService.readUserMe()
console.log(user.github_installation_id) // 12345678 or null
```

## Testing

Để test các thay đổi:

1. **Start service:**
   ```bash
   cd services/ai-agent-service
   uvicorn app.main:app --reload --port 8001
   ```

2. **Test API:**
   ```bash
   # Get current user
   curl -X GET "http://localhost:8001/api/v1/users/me" \
     -H "Authorization: Bearer <token>"
   
   # List all users (admin)
   curl -X GET "http://localhost:8001/api/v1/users/" \
     -H "Authorization: Bearer <admin_token>"
   ```

3. **Regenerate frontend client:**
   ```bash
   cd frontend
   npm run generate-client
   ```

## Migration Notes

- **Không cần database migration** vì chỉ thay đổi response schema, không thay đổi database structure
- **Backward compatible** vì field mới là optional (`Optional[int] = None`)
- **Frontend cần regenerate API client** để có type definitions mới

## Performance Considerations

- **Eager loading** giảm số lượng queries từ N+1 xuống còn 2 queries (1 cho users, 1 cho installations)
- **Minimal overhead** vì chỉ load installation_id, không load toàn bộ installation data
- **Caching** có thể được implement ở frontend level nếu cần

## Next Steps

1. ✅ Update schema với `github_installation_id` field
2. ✅ Implement helper function `user_to_public()`
3. ✅ Update tất cả route handlers
4. ⏳ Regenerate frontend API client
5. ⏳ Update frontend components để hiển thị GitHub installation status
6. ⏳ Add tests cho các endpoints đã update

