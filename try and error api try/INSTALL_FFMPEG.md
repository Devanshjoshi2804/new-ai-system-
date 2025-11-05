# Install FFmpeg (Final Step!)

Good news: **Python ✅** and **Whisper ✅** are already installed!

You just need **FFmpeg** to handle .opus audio files.

## Option 1: Install via Chocolatey (Recommended - Easiest)

### Step 1: Install Chocolatey (if not already installed)
**Run PowerShell as Administrator** and paste this:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

### Step 2: Install FFmpeg
```powershell
choco install ffmpeg
```

### Step 3: Restart PowerShell and verify
```bash
ffmpeg -version
```

---

## Option 2: Manual Installation (If Chocolatey doesn't work)

### Step 1: Download FFmpeg
1. Go to: https://www.gyan.dev/ffmpeg/builds/
2. Download: **ffmpeg-release-essentials.zip** (latest version)

### Step 2: Extract and Install
1. Extract the zip file
2. Rename the folder to `ffmpeg`
3. Move it to `C:\ffmpeg`

### Step 3: Add to PATH
1. Press `Win + R`, type `sysdm.cpl`, press Enter
2. Go to **Advanced** tab → **Environment Variables**
3. Under **System variables**, find **Path**, click **Edit**
4. Click **New** and add: `C:\ffmpeg\bin`
5. Click **OK** on all windows

### Step 4: Restart PowerShell and verify
```bash
ffmpeg -version
```

---

## Option 3: Portable (No Installation)

If you don't want to install FFmpeg system-wide, you can use it portably:

1. Download from: https://www.gyan.dev/ffmpeg/builds/
2. Extract anywhere (e.g., in this project folder)
3. Whisper will auto-detect FFmpeg if it's in the same folder

---

## After FFmpeg is installed

Test your setup:
```bash
.\test-whisper.bat
```

If all checks pass, you're ready to transcribe! 🚀

Quick test:
```bash
python transcribe-opus.py your_voice_note.opus
```

