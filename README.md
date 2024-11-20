# babycam-django

Turn your old phone and laptop into a baby camera+monitor for multiple parents and kids!

## System Diagram

```mermaid
graph TB
    subgraph "Parent Units"
        P1[Parent Unit 1] -->|HTTP/WS| API
        P1 -->|WebSocket| CH
        P2[Parent Unit 2] -->|HTTP/WS| API
        P2 -->|WebSocket| CH
    end

    subgraph "Kid Rooms"
        K1[Kid Room Device 1] -->|CamON Stream| WS[(WebSocket Server)]
        K2[Kid Room Device 2] -->|CamON Stream| WS
    end

    subgraph "Server Components"
        subgraph "Django Backend"
            WS -->|Audio Stream| AM[Audio Monitor Service]
            AM -->|Analyze Levels| AL[Audio Level Detection]
            AL -->|Store Events| DB[(PostgreSQL)]
            AL -->|Notify| CH[Channels/WebSocket]
            
            AM -->|If Alert| REC[Recording Service]
            REC -->|Save| DISK[Disk Storage]
            
            API[Django REST API] -->|Query| DB
            ADM[Django Admin] -->|Manage| DB
        end
    end

    classDef django fill:#44B78B,color:white
    classDef database fill:#336791,color:white
    classDef websocket fill:#F7DF1E,color:black
    classDef device fill:#FF6B6B,color:white
    class AM,API,ADM,REC django
    class DB database
    class WS,CH websocket
    class K1,K2,P1,P2 device
```

## Project setup

On Ubuntu dev machines:

```bash
# first create a venv, then:
sudo apt-get install portaudio19-dev # pre-req for pyaudio on ubuntu
pip install -r requirements.txt
```
