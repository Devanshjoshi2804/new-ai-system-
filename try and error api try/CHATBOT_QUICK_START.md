# 🚀 Chatbot Quick Start Guide

## ✅ What's Ready

A **professional chatbot** with:
- ✅ Real-time chat interface
- ✅ PDF OCR integration
- ✅ Onboarding + KYC flow
- ✅ File upload with drag & drop
- ✅ Progress tracking
- ✅ Mobile responsive

---

## 🎯 Start in 3 Steps

### 1. Start Server
```bash
npm start
```

### 2. Open Chatbot
```
http://localhost:3000/advanced_catbox/
```

### 3. Click "Start Onboarding"
Follow the chatbot's instructions!

---

## 📸 What You'll See

### Welcome Screen
```
┌─────────────────────────────────────┐
│ 🤖 GST Onboarding Assistant         │
│ ● Online                            │
├─────────────────────────────────────┤
│ Progress: Getting started... 0%     │
├─────────────────────────────────────┤
│                                     │
│ 🤖 Welcome to GST Onboarding!       │
│    I'll help you complete your      │
│    registration in minutes.         │
│                                     │
│    [Start Onboarding]               │
│                                     │
└─────────────────────────────────────┘
```

### Chat Flow
```
🤖: What's your email?
👤: test@example.com

🤖: What's your phone?
👤: 9876543210

🤖: Upload your GST certificate
👤: [Uploads PDF]

🤖: Processing... 🔍

🤖: ✅ Extracted:
    Company: ADD A DELTA PRIVATE LIMITED
    GSTIN: 09AASC7501M2Z4
    
🤖: ✅ Account created!
    Vendor Code: ABC123
    
🤖: Now let's complete KYC...
```

---

## 🎨 Features

### Real-Time Chat
- Message bubbles
- Typing indicators
- Timestamps
- Smooth animations

### File Upload
- Drag & drop
- File preview
- Progress bar
- Instant feedback

### Progress Tracking
- Visual progress bar
- Step labels
- Percentage display

### Mobile Responsive
- Works on all devices
- Touch-optimized
- Full-screen on mobile

---

## 🔧 Configuration

### API Endpoints (Already Configured)
```javascript
// In chatbot.js
const API_BASE = window.location.origin;
const ONBOARDING_API = `${API_BASE}/api/onboarding`;
const VISION_API = `${API_BASE}/api/vision`;
```

### File Limits
- **Max Size:** 10MB
- **Allowed Types:** PDF, JPG, PNG

---

## 🧪 Test It

### 1. Email Input
```
Try: test@example.com ✅
Try: invalid-email ❌
```

### 2. Phone Input
```
Try: 9876543210 ✅
Try: 123 ❌
```

### 3. File Upload
```
Drag & drop PDF ✅
Click browse ✅
Upload .txt ❌
Upload > 10MB ❌
```

---

## 🐛 Troubleshooting

### Server Not Starting
```bash
# Check if port 3000 is in use
netstat -ano | findstr :3000

# Kill process if needed
taskkill /PID <PID> /F

# Restart
npm start
```

### Chatbot Not Loading
```
1. Check server is running
2. Open http://localhost:3000/advanced_catbox/
3. Check browser console for errors
4. Clear cache and reload
```

### File Upload Fails
```
1. Check file size (< 10MB)
2. Check file type (PDF, JPG, PNG)
3. Check network tab in DevTools
4. Verify server logs
```

---

## 📊 Debug Mode

### Open Browser Console
```javascript
// View state
window.chatbot.state

// View messages
window.chatbot.state.messages

// View session ID
window.chatbot.state.sessionId

// Manual actions
window.chatbot.startOnboarding()
window.chatbot.sendMessage()
```

---

## 📁 Files

```
advanced_catbox/
├── index.html          ← Chat UI
├── styles.css          ← Styling
├── chatbot.js          ← Logic
└── README.md           ← Full docs
```

---

## 🎯 Next Steps

### Customize
1. Edit colors in `styles.css`
2. Modify messages in `chatbot.js`
3. Add your logo

### Deploy
1. Set up production server
2. Configure HTTPS
3. Update API endpoints
4. Add analytics

### Enhance
1. Add voice input
2. Multi-language support
3. Dark mode
4. Chat history

---

## 📚 Documentation

- `advanced_catbox/README.md` - Complete docs
- `CHATBOT_IMPLEMENTATION_PLAN.md` - Implementation plan
- `CHATBOT_COMPLETE.md` - What was built
- `METADATA_VS_KYC_EXPLANATION.md` - API structure

---

## ✅ Quick Test Checklist

- [ ] Server starts successfully
- [ ] Chatbot loads in browser
- [ ] "Start Onboarding" button works
- [ ] Email input validates correctly
- [ ] Phone input validates correctly
- [ ] File upload shows preview
- [ ] PDF OCR extracts data
- [ ] Progress bar updates
- [ ] Vendor code is received
- [ ] Mobile view works

---

## 🎉 You're Ready!

**The chatbot is fully functional and ready to use!**

Just run:
```bash
npm start
```

Then open:
```
http://localhost:3000/advanced_catbox/
```

**Enjoy your professional chatbot!** 🚀

---

## 💡 Pro Tips

1. **Keep Console Open** - See real-time logs
2. **Test on Mobile** - Use Chrome DevTools device mode
3. **Try Error Cases** - Test validation
4. **Monitor Network** - Check API calls
5. **Read Logs** - Server logs show detailed info

---

**Need Help?** Check `advanced_catbox/README.md` for detailed documentation!
