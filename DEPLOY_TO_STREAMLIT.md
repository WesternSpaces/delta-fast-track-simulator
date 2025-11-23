# Deploy to Streamlit Cloud - Final Steps

## ✅ What's Already Done

- [x] Python dependencies installed locally
- [x] Code tested and verified
- [x] Git repository initialized
- [x] GitHub repository created
- [x] Code pushed to: **https://github.com/WesternSpaces/delta-fast-track-simulator**

## 🚀 Next Step: Deploy to Streamlit Cloud (3 minutes)

### 1. Go to Streamlit Cloud

Open this link in your browser:
**https://share.streamlit.io/**

### 2. Sign In

Click "Sign in" and choose "Continue with GitHub"

### 3. Deploy the App

1. Click the **"New app"** button (top right)

2. Fill in the form:
   - **Repository:** `WesternSpaces/delta-fast-track-simulator`
   - **Branch:** `main`
   - **Main file path:** `fast_track_simulator.py`
   - **App URL (optional):** Choose a custom subdomain like `delta-fast-track`
     (Will become: https://delta-fast-track.streamlit.app)

3. Click **"Deploy!"**

4. Wait 2-3 minutes while it builds...

### 4. Your App is Live! 🎉

Once deployment completes, you'll get a URL like:
**https://delta-fast-track.streamlit.app** (or whatever you chose)

Share this URL with your focus group members!

---

## 🧪 Test Locally First (Optional)

To run the simulator on your computer before deploying:

```bash
cd "/Users/sarah/Documents/Western Spaces/Claude/delta/meeting-one"
python3 -m streamlit run fast_track_simulator.py
```

It will open in your browser at http://localhost:8501

Press `Ctrl+C` in Terminal to stop.

---

## 🔄 Making Updates

When you need to update the simulator:

1. Edit `fast_track_simulator.py` with your changes

2. Push to GitHub:
   ```bash
   cd "/Users/sarah/Documents/Western Spaces/Claude/delta/meeting-one"
   git add fast_track_simulator.py
   git commit -m "Update: [describe your changes]"
   git push
   ```

3. Streamlit Cloud will automatically redeploy (takes ~2 minutes)

No need to do anything else - it auto-updates!

---

## 📱 Sharing with Your Focus Group

Once deployed, share:

**The URL:**
https://delta-fast-track.streamlit.app (or your custom URL)

**Instructions for them:**
1. Open the URL in any web browser
2. Adjust the policy sliders on the left
3. Watch the results update in real-time
4. Explore different tabs for detailed analysis
5. Download results as CSV if needed

**Best for:**
- Chrome, Safari, Firefox, Edge (any modern browser)
- Desktop, tablet, or mobile
- No installation required
- Works on any device with internet

---

## 🎬 For Your Meeting

### Before the Meeting:
1. ✅ Deploy to Streamlit Cloud (using steps above)
2. ✅ Test the app - adjust a few sliders
3. ✅ Share the URL with focus group members 24 hours before meeting

### During the Meeting:
1. Open the app on your screen/projector
2. Walk through the default 20-unit scenario
3. Ask: "What if we changed X?" → Adjust slider → Show impact
4. Use the Comparisons tab to show multiple options
5. Download results for documentation

### After the Meeting:
1. Focus group members can explore on their own time
2. You can make updates and they auto-deploy
3. Export final scenarios to share with City Council

---

## 💡 Pro Tips

**For presentations:**
- Set browser zoom to 90% for better visibility on projectors
- Use full screen mode (F11 or Cmd+Shift+F)
- Hide browser bookmarks bar
- Have backup scenarios prepared

**For exploration:**
- Start with default scenario
- Change ONE variable at a time to see isolated impact
- Use Comparisons tab for side-by-side analysis
- Download CSV files for your records

**For credibility:**
- Point to data sources (all official 2025 data)
- Show calculation transparency
- Reference the spreadsheet they already reviewed
- Emphasize this matches their existing analysis

---

## 🆘 Troubleshooting

**App won't deploy:**
- Check Streamlit Cloud deployment logs
- Verify `requirements.txt` is present
- Make sure file path is exactly `fast_track_simulator.py`

**App is slow:**
- First load takes 30-60 seconds (cold start)
- Subsequent loads are faster
- This is normal for free tier

**Forgot your app URL:**
- Go to https://share.streamlit.io/
- Sign in with GitHub
- You'll see all your deployed apps

**Want to delete/redeploy:**
- Go to app settings in Streamlit Cloud
- Click "Delete app" to start over
- Or click "Reboot app" to restart

---

## 📞 Support

**For technical issues:**
- Streamlit docs: https://docs.streamlit.io
- GitHub repo: https://github.com/WesternSpaces/delta-fast-track-simulator
- Streamlit community: https://discuss.streamlit.io

**For policy/data questions:**
- Reference the documentation files in the repo
- Check with focus group facilitators
- Review source data in `/Data` folder

---

## ✨ You're All Set!

Everything is ready to deploy. Just go to:
👉 **https://share.streamlit.io/** and follow Steps 1-4 above.

Your focus group will have a live interactive tool in less than 5 minutes!

Good luck with your meeting! 🏘️
