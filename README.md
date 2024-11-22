# babycam-django

Turn your old phone and laptop into a baby camera+monitor for multiple parents and kids!

## Features Roadmap

* ❌ Multiple parent units can view multiple kid rooms, live video+audio feeds
* ✅ Audio level detection with alerts, with customizable audio thresholds
* ✅ Video recording on alert
* ❌ Shared chat so parents can leave messages for each other
* ❌ Schedule which parent will receive alerts when kids wake up
* ❌ Ability to adjust the schedule on-the-fly
  * e.g. if mom was supposed to do the 3AM wakeup but had a rough sleep, she can set an override and go to sleep, and dad will get the alert instead

## System Diagram

```mermaid
graph TB

    subgraph "Server Components"
        subgraph "Django Backend"
            AM[Audio Monitor Service] -->|Save loud audio timestamps| DB[(PostgreSQL DB)]
            AM -->|Notify when kids loud| CH[Channels/WebSocket]
            AM -->|Save mp4 when kids loud| DISK[(Disk Storage)]
            
            API[Django REST API] -->|Query| DB
        end
    end

    subgraph "Parent's Rooms"
        P1[Parent 1 Device] <-->|HTTP/WS| API
        P2[Parent 2 Device] <-->|HTTP/WS| API
    end

    subgraph "Kid's Rooms"
        K1[Kid 1 Device] -->|HTTP Stream| AM
        K2[Kid 2 Device] -->|HTTP Stream| AM
    end

    

    classDef django fill:#44B78B,color:white
    classDef database fill:#336791,color:white
    classDef websocket fill:#F7DF1E,color:black
    classDef device fill:#FF6B6B,color:white
    class AM,API,REC django
    class DB,DISK database
    class CH websocket
    class K1,K2,P1,P2 device
```

## Project setup

### Backend
On Ubuntu dev machines:

```zsh
# first create a venv, then:
sudo apt install portaudio19-dev # pre-req for pyaudio on ubuntu
sudo apt install redis-server # needed for inter-process communication between test_monitor.py and the main django server.
pip install -r requirements.txt
```

### Frontend
```zsh
cd ./frontend
npm install
```

## Running the app

### Backend

```zsh
# Need to run it this way instead of the usual `python manage.py run_server` in order for websockets to work
# NOTE: This doesn't do hot reloading of backend changes, you'll have to ctrl+C and re-run it
python -m daphne babycam.asgi:application -b 0.0.0.0 -p 8000
```

### Frontend
```zsh
cd frontend
npm run dev
# Then alt+click the URL to open it in the browser
```
