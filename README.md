# Acoustic Messenger

Send short text messages between phones using sound waves (no internet needed).
Built with Python + Kivy, using the open-source [GGWave](https://github.com/ggerganov/ggwave) library.

## Features
- Username screen first — you must enter a username before chatting
- Black theme with a custom background image (`assets/background.jpg`)
- Text color picker (tap **Aa**: 10 presets or any `#RRGGBB` hex), remembered between launches
- Speed selector: Normal / Fast / Fastest
- Messages up to 140 bytes (including your username)

## Get the APK (GitHub builds it for you)
1. Create a new GitHub repository and upload everything in this folder
   (including the hidden `.github` folder).
2. Open the **Actions** tab and wait for **Build APK** to finish (first build takes 20–40 minutes).
3. Open the finished run and download the **AcousticMessenger-apk** artifact, unzip it and install the `.apk`.
   Android will ask you to allow installing from unknown sources and to allow the microphone.

## Run on a computer (for testing)
```
pip install -r requirements.txt
python main.py
```

## Notes
- Use two devices in a quiet room, a short distance apart, with the volume up.
- `recipes/ggwave` is a custom python-for-android recipe that compiles GGWave for Android.
  If the build fails at the ggwave step, open the Actions log and check that recipe first.
