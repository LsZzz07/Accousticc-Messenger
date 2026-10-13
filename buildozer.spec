[app]
title = Acoustic Messenger
package.name = acousticmessenger
package.domain = org.acoustic
source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 1.0
requirements = python3,kivy==2.3.0,numpy,pyjnius,android,ggwave
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/assets/icon.png

android.permissions = RECORD_AUDIO,MODIFY_AUDIO_SETTINGS
android.api = 33
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

# custom recipe that compiles the GGWave C++ library for Android
p4a.local_recipes = ./recipes

[buildozer]
log_level = 2
warn_on_root = 1
