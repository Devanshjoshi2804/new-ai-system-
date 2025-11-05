# ✅ Vector DB Deployment Checklist

Use this checklist to ensure a smooth deployment of Vector DB.

---

## 📋 Pre-Deployment (Day -1)

### Environment Preparation
- [ ] Backup MongoDB database
  ```bash
  mongodump --uri="mongodb://localhost:27017" --out=./backup_$(date +%Y%m%d)
  ```
- [ ] Backup existing uploads directory
  ```bash
  tar -czf uploads_backup_$(date +%Y%m%d).tar.gz ./uploads
  ```
- [ ] Check available disk space (need ~10x MongoDB doc size)
  ```bash
  df -h
  ```
- [ ] Verify Python version (3.8+)
  ```bash
  python --version
  ```

### Code Review
- [ ] Review all changed files
- [ ] Run linter
  ```bash
  cd backend
  pylint src/infrastructure/ai/vector_store/
  ```
- [ ] Check for security issues
- [ ] Verify no hardcoded credentials

### Testing
- [ ] Run all unit tests
  ```bash
  pytest tests/test_vector_db/ -v
  ```
- [ ] Run integration tests
  ```bash
  pytest tests/ -v
  ```
- [ ] Test on staging environment
- [ ] Verify migration script works
  ```bash
  python scripts/migrate_to_vector_db.py --dry-run
  ```

---

## 🚀 Deployment Day

### Step 1: Install Dependencies (5 min)
- [ ] Update requirements file
  ```bash
  cd backend
  git pull origin main
  ```
- [ ] Install new dependencies
  ```bash
  pip install chromadb==0.4.22 sentence-transformers==2.2.2
  ```
- [ ] Verify installation
  ```bash
  python -c "import chromadb; print('✅ ChromaDB')"
  python -c "from sentence_transformers import SentenceTransformer; print('✅ Transformers')"
  ```

### Step 2: Create Vector DB Directory (2 min)
- [ ] Create directory
  ```bash
  mkdir -p ./vector_db_data
  chmod 755 ./vector_db_data
  ```
- [ ] Verify permissions
  ```bash
  ls -ld ./vector_db_data
  ```

### Step 3: Deploy Code (5 min)
- [ ] Pull latest code
  ```bash
  git pull origin main
  ```
- [ ] Verify all files present
  ```bash
  ls -l src/infrastructure/ai/vector_store/
  ls -l src/presentation/rest/vector_db.py
  ls -l scripts/migrate_to_vector_db.py
  ```
- [ ] Check configuration
  ```bash
  grep -A 5 "Vector DB" src/infrastructure/config/settings.py
  ```

### Step 4: Start Backend (2 min)
- [ ] Stop existing backend
  ```bash
  pkill -f "python src/main.py"
  ```
- [ ] Start new backend
  ```bash
  python src/main.py &
  ```
- [ ] Wait for startup (30 seconds)
- [ ] Check logs
  ```bash
  tail -50 logs/app.log
  ```

### Step 5: Verify Health (2 min)
- [ ] Check Vector DB health
  ```bash
  curl http://localhost:8000/api/vector-db/health
  ```
- [ ] Expected response:
  ```json
  {
    "status": "healthy",
    "collections_count": 0,
    "persist_directory": "./vector_db_data",
    "embedding_model": "all-MiniLM-L6-v2"
  }
  ```
- [ ] Check main API health
  ```bash
  curl http://localhost:8000/api/health
  ```

### Step 6: Run Migration (10-30 min)
- [ ] Dry run first
  ```bash
  python scripts/migrate_to_vector_db.py --dry-run
  ```
- [ ] Review dry run output
- [ ] Run actual migration
  ```bash
  python scripts/migrate_to_vector_db.py --batch-size 5
  ```
- [ ] Monitor progress
- [ ] Check for errors in output

### Step 7: Verify Migration (5 min)
- [ ] Run verification
  ```bash
  python scripts/migrate_to_vector_db.py --verify
  ```
- [ ] Check all documents migrated
- [ ] Verify chunk counts look reasonable (30-50 per doc)
- [ ] Check Vector DB stats
  ```bash
  python scripts/vector_db_monitor.py
  ```

### Step 8: Test Functionality (10 min)
- [ ] Upload test document
  ```bash
  curl -X POST http://localhost:8000/api/partners/{partner_id}/documentation \
    -F "file=@test_doc.pdf" \
    -H "X-Tenant-ID: test"
  ```
- [ ] Verify Vector DB storage
  ```bash
  curl http://localhost:8000/api/vector-db/stats/{doc_id}
  ```
- [ ] Run test execution
  ```bash
  curl -X POST http://localhost:8000/api/testing/start \
    -H "Content-Type: application/json" \
    -d '{"partner_id": "test", "documentation_id": "{doc_id}"}'
  ```
- [ ] Check logs for Vector DB usage
  ```bash
  tail -f logs/app.log | grep -E "(🧠|📚|🔧)"
  ```

---

## 🎨 Frontend Deployment (Optional)

### If Deploying Frontend Updates
- [ ] Pull latest frontend code
  ```bash
  cd frontend
  git pull origin main
  ```
- [ ] Install dependencies
  ```bash
  npm install
  ```
- [ ] Build production bundle
  ```bash
  npm run build
  ```
- [ ] Deploy to hosting
- [ ] Verify VectorDBStatus component renders
- [ ] Check OCRReviewStep shows Vector DB status

---

## 📊 Post-Deployment Verification (30 min)

### Functional Testing
- [ ] Upload 3 different document types (PDF, JSON, YAML)
- [ ] Verify all stored in Vector DB
- [ ] Run tests on each document
- [ ] Verify improved success rates
- [ ] Check AI response times
- [ ] Verify cost reduction

### Performance Testing
- [ ] Monitor CPU usage
  ```bash
  top
  ```
- [ ] Monitor memory usage
  ```bash
  free -h
  ```
- [ ] Monitor disk usage
  ```bash
  du -sh ./vector_db_data
  ```
- [ ] Check query response times
  ```bash
  time curl -X POST http://localhost:8000/api/vector-db/query \
    -H "Content-Type: application/json" \
    -d '{"doc_id": "test", "query_text": "test", "top_k": 3}'
  ```

### Monitoring Setup
- [ ] Set up health check monitoring
  ```bash
  # Add to cron
  */5 * * * * curl -s http://localhost:8000/api/vector-db/health | grep -q "healthy" || echo "Vector DB unhealthy!"
  ```
- [ ] Set up disk usage alerts
  ```bash
  # Add to cron
  0 * * * * du -sh /path/to/vector_db_data | mail -s "Vector DB Size" admin@example.com
  ```
- [ ] Set up log monitoring
  ```bash
  # Add to monitoring
  tail -f logs/app.log | grep -E "(ERROR|❌)" | mail -s "Vector DB Errors" admin@example.com
  ```

---

## 🐛 Rollback Plan (If Needed)

### If Issues Occur
- [ ] Stop backend
  ```bash
  pkill -f "python src/main.py"
  ```
- [ ] Checkout previous version
  ```bash
  git checkout previous_commit_hash
  ```
- [ ] Reinstall dependencies
  ```bash
  pip install -r requirements-simple.txt
  ```
- [ ] Start backend
  ```bash
  python src/main.py &
  ```
- [ ] Verify system working
  ```bash
  curl http://localhost:8000/api/health
  ```

### Note on Rollback
- ✅ Vector DB is **optional** - system works without it
- ✅ MongoDB data is **unchanged** - safe to rollback
- ✅ Vector DB data can be **deleted** if needed
  ```bash
  rm -rf ./vector_db_data
  ```

---

## 📈 Success Metrics (Week 1)

### Track These Metrics
- [ ] Test success rate
  - Target: 85-95% (vs 17% before)
  - Check: Review test execution results
- [ ] AI response time
  - Target: 2-3s (vs 10-15s before)
  - Check: Review logs for adaptation times
- [ ] Cost per test
  - Target: $0.05 (vs $0.50 before)
  - Check: Review AI API usage
- [ ] Vector DB query time
  - Target: <1s
  - Check: Monitor query logs
- [ ] Disk usage
  - Target: <10x MongoDB size
  - Check: `du -sh ./vector_db_data`

### Weekly Report Template
```
Week 1 Vector DB Report
=======================

Deployment Date: [DATE]
Documents Migrated: [COUNT]
Total Chunks: [COUNT]

Performance:
- Success Rate: [XX]% (target: 85-95%)
- Avg Response Time: [X]s (target: 2-3s)
- Avg Cost per Test: $[X] (target: $0.05)
- Vector DB Query Time: [X]s (target: <1s)

Issues:
- [List any issues encountered]

Recommendations:
- [List any optimization suggestions]
```

---

## 🔧 Optimization (Week 2+)

### After 1 Week
- [ ] Review performance metrics
- [ ] Analyze failed tests
- [ ] Check chunk sizes are optimal
- [ ] Verify top_k setting is appropriate
- [ ] Consider adjusting settings

### Potential Optimizations
```python
# If documents are large
vector_db_chunk_size = 1500

# If need more context
vector_db_top_k = 5

# If need better accuracy
embedding_model = "all-mpnet-base-v2"
```

### Performance Tuning
- [ ] Monitor query patterns
- [ ] Identify slow queries
- [ ] Optimize chunk sizes
- [ ] Adjust top_k based on results
- [ ] Consider caching frequent queries

---

## 📞 Support Contacts

### During Deployment
- **Technical Lead:** [NAME]
- **DevOps:** [NAME]
- **On-Call:** [PHONE]

### Post-Deployment
- **Monitoring:** [LINK]
- **Logs:** [LINK]
- **Documentation:** [LINK]

---

## ✅ Final Checklist

### Before Going Home
- [ ] All tests passing
- [ ] Health check returns "healthy"
- [ ] Migration completed successfully
- [ ] Test documents working
- [ ] Monitoring set up
- [ ] Team notified
- [ ] Documentation updated
- [ ] Rollback plan tested

### Sign-Off
- [ ] Technical Lead approval
- [ ] DevOps approval
- [ ] QA approval
- [ ] Product Owner approval

---

## 🎉 Deployment Complete!

**Congratulations!** Vector DB is now live and improving your API testing.

### Next Steps:
1. Monitor metrics for first week
2. Collect user feedback
3. Optimize based on data
4. Plan next improvements

### Resources:
- 📖 [Quick Start](VECTOR_DB_QUICK_START.md)
- 📚 [Implementation Guide](VECTOR_DB_IMPLEMENTATION_COMPLETE.md)
- 🔄 [Migration Guide](VECTOR_DB_MIGRATION_GUIDE.md)
- 📊 [Final Summary](VECTOR_DB_FINAL_SUMMARY.md)

---

**Deployment Date:** _______________  
**Deployed By:** _______________  
**Status:** ✅ COMPLETE  
**Version:** 1.0.0
