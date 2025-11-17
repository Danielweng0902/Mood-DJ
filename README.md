# 計算機網路 Computer Network

# Socket Programming

資工3B 翁子軒

---

## Architecture

```
MoodDJ/
├── server/
│   ├── server.py              ← 主伺服器（TCP 控制 + UDP 廣播）
│   ├── peer_registry.py       ← P2P 節點註冊中心（讓 peer 互相註冊）
│
├── client/
│   ├── gui_tkinter.py         ← 主 GUI（情緒輸入 + P2P 操控）
│   ├── player.py              ← 播放端（接收 UDP 音訊）
│   ├── peer_discovery.py      ← 自動發現其他節點
│   ├── peer_streamer.py       ← P2P 轉播音訊（client ↔ client）
│   ├── client.py              ← CLI 版控制端（純文字控制，非 GUI）
│
└── utils/
    ├── encryptor.py           ← AES/Fernet 加密模組

```

## Modules

### ```server/server.py```
> server 採 TCP（控制）+ UDP（串流） 雙通道：
	•	控制面用 加密 + 分段 framing 確保可靠完整；
	•	串流面用 UDP 降延遲、可容忍少量遺失。
	•	Server 以 非阻塞 + 多執行緒：任何一個慢/斷線的 client 不會影響其他人。
	•	再用 心跳 做健康檢查，client 端可自動重連。
	•	若啟用 P2P，client 彼此也會轉播音訊封包，減輕 server 壓力，接近分散式下載/串流概念。


### ```client/peer_registry.py``` 
> peer_registry.py 是我們 P2P 的集中註冊點：peer 以 UDP 送 JSON 去註冊自己的 (ip, port)，其他 peer 以 LIST 拿到清單，接著透過 peer_streamer.py 彼此直連做分散式轉播/下載，達到 P2P 的目的。

### ```client/gui_tkinter.py```

> 主控 GUI（Tkinter）：提供一個輸入框讓使用者打心情文字。
	•	送出時透過 TCP 連線到 server/server.py，並且用 utils.encryptor 的 對稱加密 + 分段傳輸（Message split） 將指令 /prompt 安全送出、再分段接回。
    
> * Enable P2P Discovery：丟到 背景 thread 跑 peer_discovery.main()（把自己註冊到 registry，並拉取 peers 清單）。
> * Start P2P Stream：丟到 背景 thread 跑 peer_streamer.main()（基於 peers 清單去做 P2P 轉播/拉流）。
    
    
### ```client/player.py```
    
> * 這支 player 以 UDP 收 raw PCM，並用 PyAudio 或 sounddevice 直接送到音效卡
> * 它假設上游音訊參數是 s16le, mono, 44.1kHz；IP 綁定與格式要跟 ```streamer.py``` 完全對齊
> * 若要跨機或廣播，請把 bind("127.0.0.1", …) 改成 bind("0.0.0.0", …)；若 PyAudio 在 macOS 不穩，sounddevice 是穩定備援

### ```client/peer_discovery.py```
    
> 讓程式自動把自己註冊到中心，並定期抓回 peers 清單，提供給 peer_streamer 做分散式（multi-peer）音訊轉播的目標列表。它本身不傳音訊、不做解碼，只是P2P 名單同步的基礎元件
   
### ```client/peer_streamer.py```
    
> 1. 接收（listen） 來自其他節點或伺服器的音訊串流封包（UDP 傳輸）
> 2.	播放（play） 該音訊於本地音效裝置（使用 PyAudio 或 SoundDevice）
> 3.	轉播（relay） 收到的音訊資料給其他 peers，形成分散式網狀串流架構。

> * MoodDJ P2P 模組中負責「接收、播放與轉播音訊封包」的關鍵元件


> * 它讓每個客戶端不僅能當聽眾，也能成為轉播節點，構成分散式音樂串流網路（P2P Streaming Network）

## Demo Steps:

```bash
# 專案目錄
/Users/Pig0902/Documents/VScode/MoodDJ 
```

### 1. 啟動主伺服器

```bash
cd /Users/Pig0902/Documents/VScode/MoodDJ
python server/server.py
```
* 接收 client 的 /prompt 指令。
* 分析文字情緒後播放對應音樂。
* 使用 ffmpeg 將 YouTube 音樂轉為 PCM 格式並用 UDP 廣播。

### 2. 啟動 P2P 節點註冊中心

```bash
cd /Users/Pig0902/Documents/VScode/MoodDJ
python server/peer_registry.py
```

* 管理所有 client 節點
* 協助 peer_discovery 模組找出可用的其他 client
* 形成 P2P 音樂共享網絡。

### 3. 啟動 GUI 主控制端（主播）
```
cd /Users/Pig0902/Documents/VScode/MoodDJ
python client/gui_tkinter.py
```

* 提供視覺化操作介面。
* 輸入情緒文字後透過 TCP 傳給 server。
* 控制 P2P 探測與音樂轉播。

### 4. 開啟音樂播放器（UDP 接收）

```bash
cd /Users/Pig0902/Documents/VScode/MoodDJ
python client/player.py
```

* 接收 server 廣播的音樂封包
* 透過 PyAudio 或 SoundDevice 實時播放
* 支援 macOS / Windows / Linux 自動偵測音訊驅動。
    
### 5. 操作 GUI

在 GUI 視窗:

##### 1.	點擊 Enable P2P Discovery

##### 2.	點擊 Start P2P Stream

##### 3.	在輸入框輸入「心情」：
```
I feel happy
```
##### 4. 按下 Send to Server

### 6. 第二台 Client 加入（P2P 模式）

> If 有第二台電腦（同一個區網）：
> ```
> cd /Users/Pig0902/Documents/VScode/MoodDJ
> python client/peer_discovery.py
> python client/peer_streamer.py
> ```

* ```peer_discovery.py``` 會向 ```peer_registry.py``` 登記並獲取其他節點資訊
* ```peer_streamer.py``` 會從主要節點拉取音樂流，並可再轉播給第三個節點

### 7.(optional) 模擬多 Client
> 若沒有第二台電腦，則多開終端機模擬多節點：
> ```
> # 第一個播放器
> python client/player.py --port 5680
> 
> # 第二個播放器（避開埠衝突）
> python client/player.py --port 5685
> ```

* 每個 player 必須使用不同的 port，避免衝突
* 可同時接收音樂封包，驗證多 client 支援與 multi-port


### CLI（非 GUI 控制端）

```bash
cd /Users/Pig0902/Documents/VScode/MoodDJ
python client/client.py
```

Enter command:
```
/text I feel calm
```

* 將文字轉為 /prompt 指令並加密傳給 server。
* 無需 GUI，即可觸發音樂播放。
* 適合終端或無視覺介面環境測試。

#### Flowchart

```mermaid
flowchart TB
    subgraph ServerSide[Server Side]
        S1[server.py\nTCP Control (5678)\nUDP Stream Broadcaster (5680)\nHeartbeat (5690)]
        S2[peer_registry.py\nP2P Node Tracker (5700)]
    end

    subgraph ClientSide[Client Side]
        C1[gui_tkinter.py\nMain GUI Client\nTCP Control + P2P Buttons]
        C2[player.py\nUDP Audio Receiver\nPlay PCM audio]
        C3[peer_discovery.py\nAuto find peers\nRegister to Tracker]
        C4[peer_streamer.py\nP2P Relay + Playback]
        C5[client.py\nCLI Controller]
    end

    C1-- TCP 5678 -->S1
    S1-- UDP 5680 -->C2
    C1-- "Start P2P" -->C3
    C3-- UDP 5700 (LIST/Register) -->S2
    C3-- Updates peers list -->C4
    C4 -- UDP 5681 <--> otherPeers[Other Clients\n(P2P Stream)]
```

## 加分項目

- [x] +10 Multi-client connections
    - server.py 多執行緒 handle_client()


- [x] +10 Multi-process or multi-thread
    - client GUI + server 廣播皆為 Thread 非阻塞


- [x] +10 GUI
    - Tkinter 圖形介面


- [x] +5 Message split  
    ``假設你的buffer size有限，你要如何完整的傳送超過buffer size的message?``

    - send_large() / recv_large() 分段封包傳輸


- [x] +5 Use both UDP & TCP and Explain why?  
    ``在應用中同時使用到TCP&UDP的連線模式，並解釋在你的應用中為何要這樣設計(有必要性嗎)、優點是什麼   ``
    
    - TCP 控制
    - UDP 音樂串流

    * Why TCP + UDP?
 控制面（少量、需要可靠、有順序）→ TCP。資料面（音訊流、即時性）→ UDP；丟包可接受但延遲更小，適合串流/廣播。
 
| Feature | TCP | UDP | 用途 |
|--------|-----|-----|------|
| 延遲 | 高 | 低 | 音樂串流 → UDP |
| 可靠度 | 高（保證傳遞） | 低（可能掉包） | 控制訊息 → TCP |
| 傳輸順序 | 保證 | 不保證 | /prompt → TCP |
| 封包大小 | 可分段 | 需自行控制 | PCM chunk → UDP |
| 適合的任務 | 指令、訊息 | 即時資料流 | Voice/Music Streaming |


- [x] +5 Message encryption & decryption  
    ``實現訊息加密與解密，socket僅會傳輸訊息，我們如何確保訊息安全? 請解釋你的設計理念與加解密方式``
    - AES/Fernet 加密（utils/encryptor.py）
    - 原因：
        - 方便實作
        - 適合小封包、多封包的環境
        - 對稱金鑰速度比 RSA 快得多，適合即時系統
    - 威脅模型：
        - 避免被動窺探（Passive Sniffing)
        - 防止封包篡改（Tampering）


- [x] +5 Time out handling  
    ``如果有多個用戶未使用close或是閒置在連線中，我們該如何避免資源被耗盡，請設計一個能夠處理超時連線的功能``
    - socket.settimeout(60) 自動斷線


- [x] +5 Disconnection handling & Auto Reconnection handling  
    ``如果client的連線中斷了，我們要如何自動重新連線而不是重新啟動整個client``
    - client_secure.py 自動重連機制


- [x] +5 Multi Port Listing（Different Port for Different Method）  
    ``對於不同的連線需求(比方說傳送訊息、廣播、影音串流等)我們能否提供不同的port來處理不同的功能或是連線需求?``
    - 5678 / 5680 / 5690 / 5700 多通道運作

- [x] +5 Nonblocking and explain why  
    ``你的系統是否能做到Nonblocking，在處理多用戶或龐大的message時，其他功能會不會被卡住?``
    - server + heartbeat 非阻塞設計

- [x] +20 P2P  
    ``挑戰實現基於P2P的分散式下載``
    - peer_registry：節點註冊中心（P2P 的「總表伺服器」）
        * 所有 Client 啟動時會向這個註冊中心報到（register）。
        * 註冊中心會維護一份「活躍節點列表」：
        ```python
        {
          "peer1": ("192.168.0.10", 5680),
          "peer2": ("192.168.0.12", 5685)
        }
        ```
        * 當有新節點加入時，會將目前線上節點列表回傳，讓它能直接連線到其他 peer（而非透過 server
        * 等於是 P2P 網路的「入口點」（bootstrap node）
    - peer_discovery：節點發現與維護模組
        * 啟動時會連線到 peer_registry.py 拿到其他節點清單
        * 定期發送心跳訊號（heartbeat），更新「我還在線」狀態
        * 透過 TCP 或 UDP 嘗試與其他 peer 建立連線
    > 這讓每個節點都能在區網或網際網路內自動找到鄰居節點，不需要手動輸入 IP，達成自動化分散式連接。


    - peer_streamer：P2P 音樂封包轉播器（分散式下載核心）
        * 當本機收到音樂串流封包後（例如從 UDP 5680），會同時將這些封包再轉送（relay）給其他已知的 peer
        * 其他 peer 端則可直接播放這些轉播過來的封包
        這樣每個節點同時是：
	        * 🎧 「Receiver」→ 播放音樂
	        * 📤 「Transmitter」→ 再把音樂分流出去

因此整個系統就形成了去中心化的分散式串流網絡。


> 當第一個 client（主播）從伺服器獲得音樂串流後，其他 client 不再直接從 server 下載，
而是 透過節點之間（peer-to-peer）互相傳輸 音樂資料流。

* 減輕伺服器壓力（Server offload）
    → Server 只需提供最初音樂來源，後續由節點分散傳遞。
* 具備「分散式下載」特性
    → 音訊封包可從多個節點同時獲得，類似 BitTorrent 的 peer swarm 模式。
* 即時資料流（stream-based sharing）
    → 不必完整下載整首歌，而是邊接收邊播放。
    
* P2P 符合什麼？
```peer_registry``` 做 Tracker，```peer_discovery``` 註冊/拉清單，```peer_streamer``` 在 peers 間互播音訊。這已經是分散式（peer↔peer）資料交換的最小骨架；若要「分散式下載」更完整，可以把音訊拆片、不同片向不同 peers 取、最後重組（我們目前做的是即時音訊的 P2P 轉播/拉流，屬於 streaming 型的分散式傳輸）。
    
* P2P 流程圖

```
                 ┌─────────────────────────┐
                 │     Peer Registry       │
                 │ (記錄所有活躍節點)         │
                 └──────────┬──────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
┌──────────────┐                        ┌──────────────┐
│   Peer A     │                        │   Peer B     │
│ (主播/Client)│                         │ (聽眾/Client)│
│ ─ TCP → Server                        │              │
│ ─ UDP ← 音樂串流                        │ ← P2P 傳輸 ←│
│ ─ UDP → 廣播給其他 Peer                 │              │
└──────────────┘                        └──────────────┘

```

---

## LLM 使用

> 請使用 LLM 來提升你寫的 code 的品質（例如：可讀性、結構優化、去耦合、可維護性、錯誤處理…），並撰寫成一份簡易的報告，報告內容至少需包含以下議題：

### 說明 prompt 的設計與使用的大型語言模型

#### 使用的大型語言模型: <font color ="blue">**ChatGPT-5**</font>

##### 想解決需要開各種 player的問題
prompt:
```
我想讓client/gui_tkinter.py 啟用時也自動啟用 client/player.py，這樣就主要的client就不用另外去開player.py
但同時維持player.py可以自己啟用
```

![image](https://hackmd.io/_uploads/BJIiG-dxWl.png)

##### 註解

prompt
```
請給底下的程式碼適度的加上簡潔的comment，
只有關鍵部分加即可。
---
(各個程式碼)

```

##### 註解

prompt
```
client/gui_tkinter.py，
在不同環境會發生 utilts 讀不到的問題，可以怎麼解決？
```

![image](https://hackmd.io/_uploads/rJqMV-Oebe.png)


### 優化後的程式碼與原本程式碼的比較（可針對不同優化方向探討）

優化後的程式碼，從以下方面探討：
#### 可讀性：

* 註解、邏輯更清楚
* 利用 LLM 看過各檔案後，適當的註解和縮排，同時能體醒哪些功能放在哪個程式碼中

#### 結構化

* 把功能之間的分工、分開的更明確
* 雖然原先的 Code已經盡可能做到拆分，但還是會有找不到模組的情形

#### 可維護性
* LLM 自動將重複碼（如 send_large/recv_large）統一到 utils/encryptor

### 評估 LLM 的有效性與局限性

#### 有效性

* Coding能力（在足夠好的prompt底下）越來越精確了，更是熟悉了許多常見的套件和工具
* 能協助 Debug 與架構修補
    * e.g. player 卡 UI

#### 局限性

* LLM還是仰賴精確、細節的 Prompt來達到想要的效果
* **GUI 部分**，畢竟是給人用的介面，LLM更注重的比較多是「可用就好」，有達到方便人為使用還是需要人為的設計和體驗
* 容易在同樣的地方不斷出錯，原地轉圈（例如原先的套件 ```pyaudio```無法使用，還需要人為設計 Fallback 來改用 ```sounddevice```
* 對於「需要測試」、「跟硬體/裝置相關的功能」不準確
    * 即時 streaming
    * buffer size
    * blocking
* 不熟悉你的特定執行環境
* 需要提供完整錯誤訊息才能一步步改進，難一步到位

#### 錯誤處理

* 加入更保守謹慎的 ```try-except```、```BrokenPipeError```、```ConnectionResetError handler```
* Heartbeat（心跳）錯誤處理
    * 在實作階段有問說可能是什麼造成沒聽到的狀況

### 探討除了提升程式碼品質外，在這份作業中還可以如何應用 LLM

* ##### 給出主題方向的建議
    prompt
```
作業：要求用socket programming做一個應用，我希望這個應用是盡可能有趣、實用的，同時我希望實作難度不要太高，請給我一些範例應用。

```
![image](https://hackmd.io/_uploads/rkZlrZueZl.png)

(雖然最後這些主題都沒採用就是了 XD)

* ##### 串接 LLM

    * ```client/mood_analyzer.py``` 原先的構想是利用串 ```Gemini``` 來分析心情
    * 利用 LLM 可以更精確的分析，甚至讓搜尋到的音樂更精確
    * 但因為時間不足、token需要錢而作罷

* ##### 建議擴充方向

    * ```client/recorder.py``` 是後來LLM建議的，想要做到錄下周遭環境的聲音並分析來當作 ```prompt```，但需要做到這需要<font color="red">分析音檔</font>和<font color="red">LLM分析</font>，因此作罷。

* #### Code Review 與最佳化建議
    * 找出 thread 風險
    * 找出可能 deadlock 的地方

* 協助寫報告 / Demo 設計

    * ```Demo 腳本```的提醒
    * 補充：如何描述 P2P
    * 告訴我如何在Markdown語法中，設計加分項目整理表
