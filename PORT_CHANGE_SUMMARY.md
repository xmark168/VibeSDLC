# 🔄 Port Configuration Summary

## ✅ Đã cập nhật ports trong các files sau:

### Docker Configuration
- ✅ `docker-compose.prod.yml` - Frontend: 89, Backend: 8099
- ✅ `.env.production` - Default ports updated

### Documentation
- ✅ `README.docker.md` - Updated all port references
- ✅ `DOCKER_SETUP.md` - Updated port tables and commands
- ✅ `DEPLOYMENT.md` - Updated verification commands
- ✅ `PRODUCTION_CHECKLIST.md` - Updated verification and firewall
- ✅ `Makefile` - Updated display messages
- ✅ `PORTS.md` - Comprehensive port documentation (NEW)

## 🎯 New Port Configuration

| Service  | External Port | Internal Port | Access                    |
|----------|---------------|---------------|---------------------------|
| Frontend | **89**        | 80            | http://localhost:89       |
| Backend  | **8099**      | 8000          | http://localhost:8099     |

## 🚀 Quick Test

```bash
# Start services
make up

# Test frontend
curl http://localhost:89/

# Test backend
curl http://localhost:8099/api/v1/health

# View API docs
open http://localhost:8099/docs
```

## 📝 Important URLs

```
Frontend:        http://localhost:89
Backend API:     http://localhost:8099/api/v1
API Docs:        http://localhost:8099/docs
Health Check:    http://localhost:8099/api/v1/health
```

## 🔥 Firewall Commands

```bash
# UFW
sudo ufw allow 89/tcp    # Frontend
sudo ufw allow 8099/tcp  # Backend
sudo ufw enable

# Firewalld
sudo firewall-cmd --permanent --add-port=89/tcp
sudo firewall-cmd --permanent --add-port=8099/tcp
sudo firewall-cmd --reload
```

## 📚 Next Steps

1. Review `.env.production.local` and set your secrets
2. Run `make init` to deploy
3. Configure firewall rules
4. Setup reverse proxy for HTTPS (optional)
5. See `PORTS.md` for detailed port configuration

---
**All port references have been updated to use 89 (frontend) and 8099 (backend)**
