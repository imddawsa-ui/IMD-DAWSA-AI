# NILE ONE HUMAN Flutter Client

This is the cross-platform Flutter client foundation. It does not replace the existing native Android application until Android builds and integration tests are verified.

## Requirements
- Flutter stable SDK
- Android SDK for Android builds
- A running NILE FastAPI backend

## Run
```sh
cd flutter_app
flutter pub get
flutter run
```

## Backend URL
- Android emulator: `http://10.0.2.2:8000`
- Physical Android phone: use the computer's private LAN IPv4 address and configure the backend to listen on the LAN interface. Keep the Windows firewall enabled and do not expose the API to the public internet.
- Web: use an HTTPS backend URL when hosted.

The client currently implements backend URL persistence, health checks, and the basic `POST /api/chat` flow. Authentication, social features, localization, offline model inference and the rest of the NILE modules remain future integration work.
