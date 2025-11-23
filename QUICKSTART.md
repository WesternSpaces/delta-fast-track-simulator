# Quick Start Guide - Delta Fast Track Simulator

## For Sarah: Deploying to the Web

### Step 1: Install Dependencies Locally (Testing)

```bash
# Open Terminal and navigate to the project folder
cd "/Users/sarah/Documents/Western Spaces/Claude/delta/meeting-one"

# Create a virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install -r requirements.txt

# Run the simulator locally
streamlit run fast_track_simulator.py
```

The app will open automatically in your browser at `http://localhost:8501`

### Step 2: Push to GitHub

```bash
# Initialize git repository (if not already done)
cd "/Users/sarah/Documents/Western Spaces/Claude/delta/meeting-one"
git init

# Add all files
git add fast_track_simulator.py requirements.txt README.md .gitignore QUICKSTART.md

# Create first commit
git commit -m "Initial commit: Delta Fast Track Incentive Simulator"

# Create main branch
git branch -M main

# Add your GitHub repository as remote
# (First create a new repository on GitHub.com named "delta-fast-track-simulator")
git remote add origin https://github.com/YOUR_USERNAME/delta-fast-track-simulator.git

# Push to GitHub
git push -u origin main
```

### Step 3: Deploy to Streamlit Cloud (FREE!)

1. **Go to Streamlit Cloud:**
   - Visit https://streamlit.io/cloud
   - Click "Sign up" or "Sign in" with your GitHub account

2. **Deploy the app:**
   - Click "New app" button
   - Select your repository: `YOUR_USERNAME/delta-fast-track-simulator`
   - Branch: `main`
   - Main file path: `fast_track_simulator.py`
   - Click "Deploy!"

3. **Wait 2-3 minutes** for deployment to complete

4. **Your app is live!**
   - URL will be: `https://YOUR_APP_NAME.streamlit.app`
   - Share this URL with your focus group members

### Step 4: Make Updates

When you need to update the simulator:

```bash
# Make your changes to fast_track_simulator.py

# Commit and push
git add fast_track_simulator.py
git commit -m "Update: [describe your changes]"
git push

# Streamlit Cloud will automatically redeploy (takes ~2 minutes)
```

## For Focus Group Members: Using the Simulator

1. **Open the simulator** in your web browser (URL provided by facilitators)

2. **Adjust policy levers** in the left sidebar:
   - Affordability Period: How long must units remain affordable?
   - AMI Thresholds: Income limits for qualifying households
   - Density Bonus: Extra units allowed
   - Fee Waivers: What incentives to offer

3. **View results** in the main area:
   - **Developer Economics:** Will projects be financially feasible?
   - **Community Benefit:** What's the cost to the city? What do we gain?
   - **Comparisons:** How do different scenarios compare?
   - **Export:** Download results for your records

4. **Key questions to explore:**
   - What affordability period makes sense for Delta?
   - How do we balance developer feasibility with community benefit?
   - Which incentive combinations are most cost-effective?

## Troubleshooting

### Local Testing Issues

**"No module named streamlit":**
```bash
pip install streamlit pandas numpy plotly
```

**"Permission denied":**
```bash
chmod +x fast_track_simulator.py
```

**Port already in use:**
```bash
streamlit run fast_track_simulator.py --server.port 8502
```

### Deployment Issues

**"App failed to deploy":**
- Check that `requirements.txt` is in the root directory
- Verify file name is exactly `fast_track_simulator.py`
- Look at deployment logs for specific errors

**"Module not found":**
- Make sure all packages in `requirements.txt` are spelled correctly
- Try pinning to specific versions (already done in requirements.txt)

**App is slow:**
- This is normal for first load (cold start)
- After first visit, subsequent loads are faster
- Consider adding caching decorators to functions

## Tips for Presentations

1. **Pre-load the app** before your meeting (cold start can take 30 seconds)

2. **Prepare scenarios** ahead of time:
   - Current draft proposal (15 years)
   - Neighboring community comparison (30 years)
   - Alternative incentive packages

3. **Use the comparison tab** to show multiple options side-by-side

4. **Download results** before the meeting as backup

5. **Screen share tips:**
   - Set browser zoom to 90% for better visibility on projectors
   - Hide browser bookmarks bar (View > Always Show Bookmarks Bar)
   - Use full screen mode (F11 or Cmd+Shift+F)

## Data Updates

To update AMI data or fee schedules:

1. Edit the `AMI_Data` class in `fast_track_simulator.py`
2. Edit the `FeeCalculator` class for fee changes
3. Commit and push changes to GitHub
4. Streamlit Cloud will auto-deploy the updates

## Support Contacts

- **Technical issues:** sarah@westernspaces.com
- **Policy questions:** [Focus Group Facilitators]
- **Data questions:** Dynamic Planning + Science

---

**Ready to deploy?** Follow Steps 1-3 above and you'll have your simulator live on the web in under 10 minutes!
