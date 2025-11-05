# Backend Cache Management

## ✅ **Cache Cleared Successfully!**

All backend cache has been cleared:
- ✅ Python cache (`__pycache__`, `.pyc`, `.pyo`)
- ✅ Vector DB data (`./vector_db_data`)
- ✅ Flow ChromaDB (`./data/flow_chroma_db`)
- ✅ Test databases
- ✅ SQLite files
- ✅ Log files

## 🚀 Quick Commands

### Option 1: Use the Cleanup Script
```powershell
cd backend
.\clear_cache.ps1
```

### Option 2: Fresh Start (Clear + Restart Instructions)
```powershell
cd backend
.\fresh_start.ps1
```

### Option 3: Manual Commands
```powershell
# Clear Python cache
Get-ChildItem -Path . -Include __pycache__,*.pyc,*.pyo -Recurse -Force | Remove-Item -Recurse -Force

# Clear Vector DB
Remove-Item -Path ".\vector_db_data" -Recurse -Force

# Clear Flow DB
Remove-Item -Path ".\data\flow_chroma_db" -Recurse -Force
```

## 🔄 Starting Fresh Server

After clearing cache, start the server:

```powershell
# Navigate to backend
cd "D:\test of new ai system\ai\backend"

# Activate venv
.\venv\Scripts\activate

# Start server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### One-liner:
```powershell
cd "D:\test of new ai system\ai\backend"; .\venv\Scripts\activate; uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 📦 What Gets Cleared

| Item | Location | Purpose |
|------|----------|---------|
| Python Cache | `**/__pycache__` | Compiled Python bytecode |
| Vector DB | `./vector_db_data` | Document embeddings storage |
| Flow ChromaDB | `./data/flow_chroma_db` | Test flow memory storage |
| Test DB | `./test_vector_db` | Test database files |
| SQLite | `chroma*.sqlite3` | ChromaDB metadata |
| Logs | `*.log` | Application logs |
| Pytest Cache | `.pytest_cache` | Test runner cache |
| Mypy Cache | `.mypy_cache` | Type checker cache |

## 🎯 When to Clear Cache

Clear cache when you experience:

1. **Old logs showing** - Even after code changes
2. **Import errors** - After renaming/moving modules
3. **Stale data** - Old test data persisting
4. **Vector DB issues** - Corrupted embeddings
5. **Server reload issues** - Changes not reflecting

## 🔧 Troubleshooting

### Issue: "Module not found" after clearing cache
**Solution**: Restart your terminal and re-activate venv

### Issue: Vector DB still showing old data
**Solution**: 
```powershell
cd backend
Remove-Item -Path ".\vector_db_data" -Recurse -Force
Remove-Item -Path ".\data" -Recurse -Force
```

### Issue: Server still loading old code
**Solution**:
1. Stop server (Ctrl+C)
2. Run `.\clear_cache.ps1`
3. Deactivate venv: `deactivate`
4. Reactivate venv: `.\venv\Scripts\activate`
5. Restart server

## 📝 Pro Tips

### Auto-clear on restart
Add to your workflow:
```powershell
# Clear, activate, start
.\clear_cache.ps1; .\venv\Scripts\activate; uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Schedule regular cleanups
Add to your git pre-commit hook or CI/CD pipeline

### Monitor cache size
```powershell
# Check Python cache size
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Measure-Object -Property Length -Sum

# Check Vector DB size
Get-ChildItem -Path ".\vector_db_data" -Recurse | Measure-Object -Property Length -Sum
```

## ✨ Clean State Achieved!

Your backend is now:
- 🧹 **Cache-free** - No stale bytecode or data
- 🔄 **Fresh** - Ready for clean imports
- 💾 **Reset** - Empty vector stores
- 📝 **Clean logs** - No old log data

**Ready to start fresh!** 🚀

