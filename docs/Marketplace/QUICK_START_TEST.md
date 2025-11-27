# Marketplace Quick Start - Testing Guide

## Prerequisites

1. **Application Running**
   ```bash
   cd /Users/rainergeissendoerfer/my_private_code/trusted-data-agent
   python -m trusted_data_agent.main
   ```

2. **Browser Access**
   - Open: http://localhost:5001
   - Login with test user

3. **Test Data**
   - At least 1 published collection (see setup below)

---

## 5-Minute Quick Test

### Setup (Once)

1. **Create a Test Collection**
   - Navigate to RAG Maintenance view
   - Click "Add Collection"
   - Name: "Test SQL Patterns"
   - MCP Server: Select any available
   - Description: "Sample collection for marketplace testing"
   - Click "Add Collection"

2. **Add a RAG Case**
   - Select the collection
   - Click "Add Case" (or use template populator)
   - Add at least 1 case with sample data
   - Save

3. **Publish to Marketplace**
   - Use API or publish button (if available):
   ```bash
   curl -X POST http://localhost:5001/api/v1/rag/collections/<collection_id>/publish \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"visibility": "public"}'
   ```

### Test Sequence (3 minutes)

1. **Browse (30 seconds)**
   - Click "Marketplace" in sidebar
   - ✅ Verify collection card appears
   - ✅ Check metadata: name, description, owner, count, rating

2. **Search (30 seconds)**
   - Enter "SQL" in search box
   - Press Enter or click Search
   - ✅ Verify filtering works

3. **Subscribe (30 seconds)**
   - Find your published collection (test with different user if possible)
   - Click "Subscribe"
   - ✅ Button changes to "Unsubscribe"
   - ✅ Subscriber count increments

4. **Fork (30 seconds)**
   - Click "Fork" button
   - ✅ Modal opens
   - Enter name: "My Forked Collection"
   - Click "Fork Collection"
   - ✅ Success notification
   - ✅ Forked collection in RAG Maintenance

5. **Rate (30 seconds)**
   - Click "Rate" button
   - ✅ Modal opens
   - Select 5 stars
   - Enter review: "Great collection!"
   - Click "Submit Rating"
   - ✅ Success notification
   - ✅ Rating updates on card

6. **Pagination (30 seconds)** (if 10+ collections)
   - ✅ Pagination controls visible
   - Click "Next"
   - ✅ Page 2 loads
   - Click "Previous"
   - ✅ Returns to page 1

---

## Common Issues & Fixes

### Issue: Marketplace view blank
**Fix:** Check browser console for errors. Verify JWT token valid.

### Issue: Subscribe button doesn't work
**Fix:** Ensure you're not the collection owner. Check network tab for API errors.

### Issue: Fork modal won't open
**Fix:** Refresh page. Check console for JavaScript errors.

### Issue: Rating won't submit
**Fix:** Ensure you selected stars (rating required). Cannot rate own collections.

---

## Next Steps

After quick test passes:
1. Run full 30-test manual test plan (`test_marketplace_phase4_ui.md`)
2. Test with multiple users
3. Test edge cases (errors, empty states)
4. Test cross-browser (Chrome, Firefox, Safari)

---

## Test Checklist

Quick verification (5 min):
- [ ] Navigate to Marketplace view
- [ ] Search for collections
- [ ] Subscribe to a collection
- [ ] Fork a collection
- [ ] Rate a collection
- [ ] Verify pagination (if applicable)

Full verification (30 min):
- [ ] Execute all 30 test cases in `test_marketplace_phase4_ui.md`
- [ ] Document any issues found
- [ ] Test with 3+ different users
- [ ] Test in 2+ browsers

---

**Ready to Test:** ✅ All code complete, no errors detected

**Documentation:** See `docs/Marketplace/` for complete guides
