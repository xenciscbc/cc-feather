# cc-feather

[English](README.md) | **繁體中文**

Claude Code plugin：相容 codex-feather 的交接紀錄，並提供角色分派、setup 與 model 設定。需要 Python 3.11+，僅使用標準函式庫。

## 安裝

從 [GitHub](https://github.com/xenciscbc/cc-feather) 安裝，在 Claude Code 執行：

```text
/plugin marketplace add xenciscbc/cc-feather
/plugin install cc-feather@cc-feather
```

更新已安裝的 plugin 時，在 shell 執行下列指令，或在 Claude Code 的 `/plugin` 介面中更新：

```text
claude plugin update cc-feather@cc-feather
```

本機 checkout 可用 `/plugin marketplace add /absolute/path/to/cc-feather` 加入，再用相同 install 指令。開發時可用 `claude --plugin-dir /absolute/path/to/cc-feather`。安裝後開新 session；plugin 載入方式見 [Claude 官方文件](https://code.claude.com/docs/en/plugins)。之後更新 plugin 版本時，請對已安裝的項目執行 setup update，再開新 session，詳見[更新、移除與驗證](#更新移除與驗證)。

## 入口

| Skill | 用途 |
| --- | --- |
| `/cc-feather:handoff` | 保存、列出、讀取、接續工作，查詢／清除／封存完成歷史與來源基準 |
| `/cc-feather:handoff-list` | 列出交接工作摘要（唯讀，不接續） |
| `/cc-feather:handoff-save [工作]` | 保存指定工作；省略時保存目前工作 |
| `/cc-feather:handoff-resume [工作]` | 接續指定工作或唯一未完成的工作；有多項時詢問 |
| `/cc-feather:setup` | 先查狀態，分別或一起管理 handoff 自動維護規則、agent 分派規則與角色安裝 |
| `/cc-feather:delegation` | 按需載入主 Agent 的派工、審查、驗收與復原流程 |
| `/cc-feather:delegation-preview [計畫、ticket 或工作]` | 預覽工作會如何分派，不實際派工；見[分派預覽](#分派預覽) |
| `/cc-feather:model` | 查看、設定角色 model／effort，區分單次、session 與永久選擇 |
| `/cc-feather:auto-on` | 開啟依計畫施工的自動計畫審查、程式碼審查與結果驗證；主 Agent 之後可不經詢問，在通過前 commit 這類工作、推送到它為此工作建立的 branch 並開 pull request，但合併到預設 branch、release、回報完成與 ticket 完成仍需兩項通過或你的接受並合併決定 |
| `/cc-feather:auto-off` | 關閉自動審查 |

交接指令在 plugin 安裝後即可使用。Setup 可只裝 handoff 自動維護規則、只裝 agent 分派（規則＋角色），或兩者都裝。例如：

```text
/cc-feather:setup 在目前專案只安裝 agent 分派規則與角色
/cc-feather:model 顯示目前專案的角色模型設定
/cc-feather:model 將目前專案 executor 的 effort 永久改為 high
```

Setup 先查現有狀態，再補問未指定的操作、項目與範圍；寫入前會預覽，檢查衝突、備份並管理擁有權；不改主模型、並行數、settings.json 或既有交接資料。永久 model 修改寫入原生角色檔，setup 更新保留已選設定。單次指定不會修改永久設定。詳見[設定與生命週期](docs/setup.md)。

## Setup：先查狀態，再選擇項目

直接輸入 `/cc-feather:setup`，會先查目前專案及使用者範圍的安裝狀態，列出兩項是否已安裝、是否衝突或需要遷移，再詢問要安裝、更新、移除或只查看哪一項，以及操作範圍。若已指定範圍，只檢查該範圍；已說清楚的選擇不會重問。

| 可選項目 | 安裝內容 | 移除後 |
| --- | --- | --- |
| handoff | 指示檔中獨立的自動維護規則 | 只移除提醒；交接紀錄與 plugin 的 handoff 指令仍保留 |
| agent 分派（delegation） | 獨立分派規則＋八個原生 agent；自動計畫審查預設關閉 | 移除完整的受管理角色及分派規則，保留 handoff 規則 |
| 兩者（both） | 上述兩項 | 依所選操作一起處理，仍保留交接資料與其他使用者設定 |

可直接指定，不必走逐項詢問：

```text
/cc-feather:setup 在目前專案只安裝 handoff 自動維護規則
/cc-feather:setup 在目前專案只安裝 agent 分派規則與角色
/cc-feather:setup 在目前專案兩者都安裝
/cc-feather:setup 只更新目前專案的 handoff 規則
/cc-feather:setup 只移除目前專案的 agent 分派，保留 handoff
/cc-feather:setup 查看使用者範圍的安裝狀態
```

「兩者都安裝」只補上尚未安裝的項目；「更新兩者」只更新已安裝項目；「移除兩者」只移除已安裝項目。已存在或不存在的另一項不會因此被重設。

兩項在該範圍的指示檔中各有獨立的管理區塊，安裝狀態在各範圍的 `cc-feather/state.json` 分項保存。handoff 規則不會自行建立新紀錄：仍需使用者要求建立或接續後，才在里程碑、受阻與完成時維護同一份紀錄。只查看／列出不啟用維護。

舊版將兩種規則放在同一區塊；升級會檢查擁有權並拆分，保留模型與審查設定。只移除分派不能順便刪掉原有 handoff 提醒；既有檔案被修改或名稱衝突時，先保留並交由使用者決定。

## 日常使用流程

1. 在要工作的專案開啟 Claude Code，安裝 plugin。交接功能可直接使用。
2. 可用 setup 安裝 handoff 規則、agent 分派或兩者。要只啟用角色分派，執行 `/cc-feather:setup 在目前專案只安裝 agent 分派規則與角色`；若要跨專案使用，明確改成「在使用者範圍安裝」。完成後開新 session。安裝前請先移除或停用 Claude 會載入的 instruction 檔（包含使用者範圍的 CLAUDE.md）中其他的委派或 orchestration 規則與 agents：cc-feather 不會偵測它們，兩套規則會同時生效，可能互相矛盾。
3. 直接描述工作，主 Agent 依任務分派；也可以點名角色或指定模型。小型工作仍由主 Agent 直接完成。
4. 需要跨 session 接續時，用 `/cc-feather:handoff 保存目前工作`；下次用 `/cc-feather:handoff 接續指定工作`。

例如，以下都是對 Claude 的自然語言要求，不是額外的 slash commands：

```text
請用 scout 找出登入 API 的路由和對應測試，只回報位置。
請用 Explore 探索登入流程涉及哪些模組及呼叫關係。
請用 analyst 分析登入失敗的原因，先不要修改程式。
請用 analyst 專注審查登入流程的授權與 session 安全問題。
請用 executor 實作已確認的登入錯誤處理方案。
請用 mech-executor 按照這份對照表批次改名，不改變行為。
請用 security-executor 修正已確認的越權問題，驗證允許與拒絕案例。
請用 Sonnet 審查這份實作計畫。
```

## 設定與變更模型

```text
/cc-feather:setup 檢查目前專案的安裝狀態與自動審查模式
/cc-feather:model 顯示目前專案的角色 model 和 effort
/cc-feather:model 本次 session 的 analyst 使用 Sonnet，effort 維持 high
/cc-feather:model 將目前專案 executor 的 model 永久設為 Opus，effort 設為 medium
/cc-feather:model 將使用者範圍 Explore 的 model 永久設為 Haiku，effort 設為 low
```

單次工作指定優先於 session 偏好和永久設定；未指定的欄位保留角色設定。Session／單次設定需要 Claude 原生參數支援；若當前工具不能覆寫 effort，會說明限制，改用新 session 的設定匯出或你選擇的永久修改，不會把 prompt 文字當成模型綁定。

## 分派與預設模型

| 角色 | 原生名稱 | Model | Effort |
| --- | --- | --- | --- |
| 事實查找 | scout | sonnet | low |
| 廣域探索 | Explore | sonnet | low |
| 分析／安全分析／計畫審查 | analyst | opus | high |
| 機械式實作 | mech-executor | sonnet | medium |
| 一般工程實作 | executor | opus | medium |
| 安全敏感實作 | security-executor | opus | high |
| 實作後驗證 | verifier | opus | high |
| 實作後程式碼審查 | reviewer | opus | high |

| 角色 | 何時使用 | 產出與權限 |
| --- | --- | --- |
| scout | 範圍明確的事實查找，例如定位定義、設定或引用 | 唯讀；回報檔案位置與證據，不做複雜因果分析 |
| Explore | 尚不清楚程式結構，需要較廣的模組、入口、呼叫關係探索 | 唯讀；建立理解程式的地圖，深入診斷交給 analyst |
| analyst | 根因／影響分析、安全問題查找、實作前計畫審查 | 唯讀；回報證據、推論與建議；計畫審查回覆 READY／REVISE |
| mech-executor | 規則、範圍與結果已明確的重複修改 | 可修改指定檔案；按完整規格執行，例如批次改名 |
| executor | 需要局部設計與工程判斷的功能或修正 | 可修改指定檔案並驗證，遇到架構或需求缺口交回主 Agent |
| security-executor | 影響授權、秘密資料、密碼學或信任邊界的實作 | 可修改指定檔案；驗證正常行為及濫用／拒絕案例 |
| verifier | 獨立確認完成的實作是否符合明確的 claim | 執行檢查與反例，不修改檔案；回覆 CONFIRMED／REFUTED／INCONCLUSIVE |
| reviewer | 獨立審查實作某個 claim 的程式碼 | 自行從 base revision 取得 diff，可跑不改檔的靜態檢查，不修改檔案也不跑測試；回覆 APPROVED／CHANGES_REQUESTED |

主 Agent 保留需求理解、決策、整合與最後驗收。小型或脈絡高度耦合的工作直接處理；獨立子任務才分派，明確指定範圍、檔案 ownership 與完成條件。子 Agent 都是 leaf，不再往下分派，也不維護交接或進度紀錄，改由主 Agent 依其回報記錄。

每個欄位獨立套用優先序：**該次任務明確指定 > 適用的 session 指定 > 已儲存角色設定 > 套件預設**。例如「用 Sonnet 審查計畫」仍使用 analyst 職責，model 改為 Sonnet，未指定 effort 則保留 analyst 的 high。指定值無法原生套用時先說明，不暗中替換或只在 prompt 假裝設定成功。

安全分析由唯讀 analyst 做；涉及實際安全邊界的實作交給 security-executor。

自動審查預設關閉，用[開關](#自動審查開關)開啟或關閉。開啟後只涵蓋**依計畫施工的工作**：依你同意的計畫、spec、ticket 或對話中的計畫進行的工作。

| 步驟 | 時機 | 角色 | 通過條件 |
| --- | --- | --- | --- |
| 計畫審查 | 施工前 | analyst | READY |
| 程式碼審查 | 主 Agent 的主要驗收通過後 | reviewer，自行取得 diff | APPROVED |
| 結果驗證 | APPROVED 之後 | verifier | CONFIRMED |

- **沒有計畫的工作**不自動審查；但改動安全邊界、遷移資料或不可逆操作，須先寫出計畫、通過審查並經你同意才施工。
- **次數上限：**每個步驟計算連續沒通過的自動呼叫次數：計畫審查以計畫計，程式碼審查與驗證以 claim 計。自動呼叫通過就歸零；連續兩次沒通過，該步驟停下，不等於通過，工作會等你決定。失敗、中斷或回覆不合格式的呼叫也算一次；同一 session 內改名、換 reviewer 或換模型都不會歸零；恢復的 session 重新計數。
- **施工中的重審：**只有重大偏離，也就是改變計畫的結果、範圍或驗收條件，才會重審計畫。受影響的後續工作會停下，修訂後的計畫要通過計畫審查並經你同意才繼續。措辭調整或在已同意的結果、範圍與驗收條件內的修改，不會重審計畫；相關程式碼仍隨所屬 claim 經過程式碼審查與驗證。
- **問題分級：**阻擋性問題（正確性、安全、資料遺失、regression、偏離計畫）必須修正或附證據駁回；非阻擋問題列在最終回報，有進行中的交接時另建獨立的後續工作。
- **未通過：**沒拿到 APPROVED 的 claim 視為未審查，不進入預設 branch、不 release、不回報完成。REFUTED 後的修正會先再經過程式碼審查，才交給 verifier 複驗。沒有有效 CONFIRMED 的 claim 視為未驗證，同樣不進入預設 branch、不 release、不回報完成。驗證次數跨修正累計，只有自動的 CONFIRMED 才歸零，所以連續兩次 REFUTED 的 claim 在一輪修正複驗後就會停下。有進行中的交接時，會記下尚未解決的結論。通過其中一關後，記錄會改成這個 claim 待驗收，並寫明還缺什麼；只有在 claim 進入預設 branch、release、回報完成，或取消且其 commit 已有決定時才移除，所以單靠一次通過（例如 `off` 下明確要求的審查）絕不會讓 claim 進入預設 branch。延後時記錄保留，豁免也會繼續記在裡面。唯一例外是你決定接受並合併（見你的決定）。
- **有效範圍：**通過只對它審過的內容有效。改動 claim 的檔案或其相依項目，會重新打開程式碼審查與驗證；只改環境則只重新打開驗證；其他改動，主 Agent 會說明為什麼通過仍然有效。更新 ticket 狀態不會重新打開任何步驟。重新打開的步驟沿用原本的次數，自動通過後是零；若是明確通過解除了停止，重新打開的呼叫仍需要你再要求。
- **Commit 條件：**在 auto 下，主 Agent 可以不經詢問，在依計畫施工的 claim 通過前先 commit，推到它為這項工作建立的 branch，並開 PR 列出尚未驗收的 claim。要推到原本就存在、不是它建立的 branch 前，會先問你；恢復的 session 裡，只有進行中的交接記錄了它為這項工作建立該 branch，才算它自己的 branch。受把關約束的審查或驗證需要 commit 時，主 Agent 才會先 commit。開 PR 不等於可以 merge，通過也不代表要 land 或 release；你明確說不要 commit 或不要 push 時，以你的指示為準，因此審查或驗證缺少所需 commit 時，該 claim 會回報為受阻。只因進行中的交接記錄為未審查、未驗證或待驗收而受把關的 claim，主 Agent 可以不經詢問做審查或驗證所需的本機 commit，但 push 與開 PR 會先問你，和 `off` 相同。以上 claim 都只有在 APPROVED 與 CONFIRMED 都仍有效，或你決定接受並合併時，才會讓 claim 進入遠端的預設 branch、release、回報完成或把 ticket 設成完成。取消的 claim 留在 branch 上的 commit 會一直列為未驗收，直到你決定用新 commit revert、不讓它進入預設 branch，或接受並合併；在那之前，帶著它們的 branch 不會被合併。已推送的歷史不會改寫，修正一律加新 commit；合併一個 branch 就等於合併上面所有 claim。這類 claim 的每次審查與驗證，都針對指名的 commit，且工作區乾淨。預設 branch 指遠端 HEAD 所在的 branch，或你指定為受保護或共用的 branch。在預設 branch 上，通過前的 commit 會標示為未驗收，要等兩關都通過、你決定接受並合併，或你明確允許才會推送；在那之前，主 Agent 會提醒你環境回收時這些 commit 會遺失。`off` 下其他行為不變。
- **事後檢查：**只有在授權操作之後才會存在的驗收項目（例如 commit 之後的 tag），由主 Agent 在操作後檢查並回報；其餘部分在操作前驗證。
- **你的決定：**步驟等你決定時，主 Agent 會把你的決定記為重審、延後、取消、修改驗收、豁免或接受並合併其中一種，並註明範圍。豁免會寫明它豁免的是哪個問題或缺少的哪一關，連同剩餘風險持續列出，絕不記為 READY、APPROVED 或 CONFIRMED，所以受驗收把關約束的 claim 被豁免後，要等之後的審查或驗證通過，或你決定接受並合併，才會進入預設 branch、release 或回報完成。你允許的工作中途推送可以把它的 commit 推到預設 branch，但不算 release，也不算完成。接受並合併是你明確接受某個 claim，即使它缺少一關或兩關：主 Agent 會記下所接受的 commit、缺少的關卡與剩餘風險，在回報與進行中的交接中持續列出，之後驗收把關就不再擋下該 claim 的合併、release 或完成；之後若有相關變更就失效，記在進行中交接的決定在恢復的 session 仍然有效，直到發生這種變更。你說工作已完成，要等主 Agent 向你確認並記為接受並合併，才算驗收；說「繼續」或關掉 auto，都不代表接受已知的缺陷。
- **授權：**通過不代表新的授權；READY 且原本已有授權的工作直接繼續，不固定再問一次。
- **明確要求**計畫審查、程式碼審查或驗證時不受開關限制，只執行你要求的那一項，也不佔自動次數；其結論也不會讓任何步驟的次數歸零。在 auto 下，若它讓自動流程已停下的步驟通過，自動流程會從那裡接續。
- **停下之後：**你明確要求再跑已停下的步驟並通過時，停止狀態解除，次數維持在停下時的數字，在 auto 下自動流程接著進入下一步。因為次數沒有歸零，同一份工作在該步驟之後的自動呼叫（例如修正後的審查）都需要你要求；那次呼叫仍屬於自動流程，通過就歸零，沒通過就再次停下。自動流程還沒走到該步驟前所做的明確審查或驗證，不算該步驟的通過。
- **要求審查時：**在 auto 下，你要求的審查若正好是流程該跑的步驟，就算自動呼叫；若該步驟已停下或不在流程中，就算明確要求；主 Agent 派出前會先說明是哪一種。已實作但這個 session 沒有計畫審查紀錄的工作，主 Agent 會先照「實作完才做計畫審查」問你。
- **實作完才做計畫審查：**在 auto 下，工作已經實作，但這個 session 沒有它的計畫審查紀錄（沒有自動計畫審查，你也沒對它做過決定），例如在另一個 session、Claude 以外或 review 為 off 時實作的，主 Agent 會在任何審查前先問你：要先補計畫審查，還是直接做程式碼審查。它會列出找到的先前計畫審查紀錄，但不把它當成通過。先補計畫審查算一次自動呼叫，審查整份計畫；直接做程式碼審查則把缺少的 READY 記為已實作 claim 的豁免。尚未實作的 claim 仍會先做計畫審查。這個 session 自動流程已經審查過、停下或你已決定過的計畫照一般規則處理，不會再問。
- **重試：**每次嘗試的呼叫都算一次，包括暫時失敗後的一般重試；已停下的步驟不會以重試名義再派出。派出前就發現角色或新 context 不可用，不算一次呼叫。
- **狀態不明：**這個 session 中無法確定次數、結論或阻擋事項時（例如 context 壓縮後；壓縮不算新的 session），主 Agent 會視為已停下並問你。每次審查結果都會附上目前的次數。
- **成本：**在一個 session 內一次不中斷的完成過程中，一份有 N 個 claim 的計畫至少自動呼叫 1 + 2N 次，最多約 2 + 6N 次，因為每個 claim 最多六次（修正前後各兩次程式碼審查、兩次驗證）；重新打開的 claim 與每次經你同意的重大偏離都會再增加呼叫，每次偏離最多兩次計畫審查；預設角色都是 opus/high。要降低成本，用 `/cc-feather:model` 調整角色，例如 `verifier.effort=medium`；package 預設不變。計畫要切成多細的 claim，由寫計畫的地方決定（例如 spec、規劃或切票的 skill），不是 cc-feather。
- **獨立性：**每次審查都在新的 context 中自行取得證據，但通常和主 Agent 用同一個模型。想要模型多樣性，可用 `/cc-feather:model` 把 analyst 或 reviewer 設成其他模型。cc-feather 看不到也無法保證主 Agent 的模型；換角色模型不會讓該步驟的次數歸零。若你有其他廠商的模型，可另外明確要求第二意見，它不屬於這個流程。

**哪份文件是計畫。**計畫就是你要求主 Agent 實作時指名的那份文件；指名即代表你同意它。

- **一份 spec，或其中幾張 ticket：**該 spec 連同這些 ticket 是一份計畫，只做一次計畫審查。範圍內每張未完成的 ticket 是一個 claim，它的 `Blocked by` 行就是相依關係。
- **單一 ticket：**該 ticket 就是計畫，其 spec 作為背景提供給計畫審查、程式碼審查與結果驗證。
- **不屬於任何 spec 的 ticket** 自成一份計畫。**沒有 ticket 的 spec** 沿用它列出的 claim；沒有列出時整份是一個 claim。
- **例子：**`docs/specs/login.md` 有尚未完成的 ticket 01、02、03，且 03 `Blocked by` 02。「實作 login spec」是一份有三個 claim 的計畫：計畫審查一次，03 等 02 完成。在新 session 中「實作 ticket 02」，則 ticket 02 是計畫，`login.md` 作為背景。
- **已涵蓋：**若這個 session 已有計畫涵蓋你指名的工作，就沿用該計畫，不重做計畫審查，保留它的次數、結論與阻擋事項。指名單一 ticket 既不會重複審查，也無法繞過已停下的審查。
- **部分重疊：**新計畫若與這個 session 既有的計畫部分重疊，重疊的 ticket 會承接既有計畫尚未解決的結論與阻擋事項。若既有計畫已停下，重疊的工作保留它的次數與停止狀態，不會多出新的自動呼叫：新計畫的自動 READY 不會解除那個停止，涵蓋這些工作的明確通過才會。互不相關的新工作另外計數。
- **恢復的 session：**進行中的交接若記錄了某份 spec 計畫尚未解決的結論，之後指名該 spec 的 ticket 時仍然適用；反過來，記錄在某張 ticket 計畫上的結論，之後指名整份 spec 時仍會限制那張 ticket。不論 auto 或 off，這兩種限制都會持續到之後的審查通過，或你取消工作、修改驗收或豁免為止；要求重審時，只有那次審查通過才會解除限制，延後則保留限制。次數與通過的結論不會帶到新的 session：在 auto 下，未完成的計畫會重新審查；不論哪種模式，已完成的 ticket 都不會重做。沒有進行中的交接記錄時，不會有任何限制帶過去。在進入預設 branch、release 或回報完成前，之前 session 通過的 claim 要重新審查與驗證；只有 ticket 是在兩關通過或你決定接受並合併之後才設成表示已完成的完成值、且之後沒有相關變更的 claim 例外。交接記錄為待驗收的 claim 仍受把關，在新的 session 要重新通過兩關，除非記錄裡有你接受並合併的決定且之後沒有相關變更，或它的 ticket 已如上所述設成表示已完成的完成值。已有 claim 實作的計畫，主 Agent 會先照「實作完才做計畫審查」問你。
- **沒有剩餘工作：**指名範圍內的 ticket 都已完成時，主 Agent 會回報沒有剩下要實作的部分。
- **Ticket 狀態：**claim 通過且 commit，而且若有 release tag 這類事後檢查項目，也已成立之後，主 Agent 會把它的 ticket 設成你的 tracker 慣例定義、表示已完成的完成值（例如 `resolved`），並註明版本或 commit；沒有定義時，只回報它認為已完成的 ticket。你決定接受並合併後，主 Agent 也會這樣做，並註明這個決定與剩餘風險。ticket 的狀態等於慣例定義的任一完成值（例如表示不會做的值），或你說它已完成，才算完成；沒有定義完成值時主 Agent 會問你。完成只代表不再重做：ticket 要在兩關通過或你決定接受並合併之後才設成表示已完成的完成值，且之後沒有相關變更，才算已驗收；表示不會做的值（例如 `wontfix`）只在你取消時設定，絕不算驗收。
- **辨識 ticket：**主 Agent 依明確連結（例如 `Spec:` 行或 parent 參照）、同一個功能目錄，或你直接指名，來辨識 spec 的 ticket。主 Agent 會先看專案指示（CLAUDE.md 或 AGENTS.md，以及它們指向的檔案）有沒有寫 ticket 放在哪裡。沒有寫就自己找；全 repo 搜尋可能跳過版本控制忽略的檔案和隱藏目錄，所以搜不到不代表沒有，還會直接查看可能放 ticket 的被忽略或隱藏目錄。你指名的內容對不上任何計畫或對上多份時會詢問，並說明實際採用了哪些 ticket。仍然找不到 spec 的 ticket 時：spec 自己列了 claim 就沿用那份清單；spec 提到自己的 ticket 或 claim 卻沒列出 claim，主 Agent 會在計畫審查或實作前問你，要指出它們的位置，還是當成一個 claim；沒提到這些的 spec 算一個 claim，前提是它有自己的驗收條件。預覽會標示提到自己的 ticket 或 claim 卻找不到的計畫。
- **告訴主 Agent ticket 放在哪裡：**在專案的 CLAUDE.md 或 AGENTS.md（或它們指向的檔案）寫一行，說明 spec 和 ticket 放在哪裡，例如「Tickets: `.scratch/<feature>/issues/`, linked to specs in `docs/specs/` by a `Spec:` line」。規劃工具的 setup 可能會幫你寫好這行。如果這份指示檔沒有進版本控制，其他 checkout 就沒有這行，主 Agent 只能退回自己搜尋。
- **不一致：**spec 自己列了 claim 又有 ticket 時，列出的 claim 必須與它所有的 ticket（不論是否完成）一致；不一致會列為阻擋事項，由你決定。
- **修改 claim：**主 Agent 不會為了補 claim 而修改 spec 或 ticket，除非你授權：審查需要新增、拆分或修改 claim 時，由你或你的規劃步驟決定；主 Agent 在你授權後才修改，並保留新舊 claim 的對應與尚未解決的阻擋事項。
- **還不算計畫：**既沒有 ticket、也沒有自己範圍與驗收條件的 spec（例如沒有驗收段落的 spec 範本）還不算計畫；主 Agent 會先補齊，並請你確認補齊後的版本。
- **plan mode 與對話中的計畫：**它們的 claim 只存在於該計畫的文字中，其他 session 看不到；這是已接受的限制。新的 session 只會依它的原文、現有紀錄或你確認過的版本來使用這類計畫。
- **檔案位置：**spec 放在哪裡、ticket 是否 commit，不由 cc-feather 決定；它使用實作的 session 手上有的檔案。

完整規則見[計畫審查](skills/delegation/references/plan-review.md)、[程式碼審查](skills/delegation/references/code-review.md)與[結果驗證](skills/delegation/references/outcome-verification.md)程序；用語定義見 [CONTEXT.md](CONTEXT.md)。

### 自動審查開關

```text
/cc-feather:auto-on
/cc-feather:auto-off
/cc-feather:auto-on project
/cc-feather:auto-off user
```

不帶參數（或加 `session`）只影響目前 session；加 `project` 或 `user` 則永久儲存至該範圍既有的 setup 安裝。保留 Claude plugin 的 `cc-feather:` 命名空間，指令名稱不再重複 `feather-`。

預設 `off` 不自動觸發；開啟後的 `auto` 審查依計畫施工的工作，並讓主 Agent 不經詢問，在 claim 通過前先 commit、推到它為這項工作建立的 branch，以及開 PR 列出尚未驗收的 claim；進入預設 branch、release、回報完成與把 ticket 設成完成，仍要等兩關都通過，或你明確決定「接受並合併」（見上方 Commit 條件與你的決定）；兩者都接受明確要求的審查。永久設定不會取消另行指定的單次／session 偏好。可用 setup 查詢已儲存模式；更新保留永久選擇，切換不會讓既有計畫或 claim 的各步驟次數歸零。

永久模式儲存位置如下；請透過指令修改，避免手動編輯管理區塊造成擁有權衝突。

| 範圍 | 載入給 Claude 的政策 | 同步管理狀態 |
| --- | --- | --- |
| project | `<專案>/CLAUDE.md`、`.claude/CLAUDE.md` 或 AGENTS.md（見下方） | `<專案>/.claude/cc-feather/state.json` |
| user | `<Claude 設定目錄>/CLAUDE.md` | `<Claude 設定目錄>/cc-feather/state.json` |

Claude 設定目錄預設是 `~/.claude`，可由 `CLAUDE_CONFIG_DIR` 指定。`auto` 時分派區塊包含自動審查規則，`off` 時整段移除，主 Agent 與子 Agent 都不會載入。專案範圍的 `off` 會保留一行「此專案關閉自動計畫審查」的說明，因此覆蓋使用者範圍的 `auto`：任務／session 選擇優先，其次是專案指示，最後是使用者指示。較早版本以 `off` 安裝的專案，要到下次執行 review 或 setup update 才加入這一行。較早版本的安裝保留 `Automatic plan review mode:` 那行，執行 setup update 後改為新格式。永久開關需要先安裝該範圍的 agent 分派；只有 handoff 規則不夠；新 session 載入已儲存模式。

project 範圍會寫進既有的 CLAUDE.md，沒有的話寫進 `.claude/CLAUDE.md`。Claude Code 只在沒有任何 CLAUDE 檔時才讀 AGENTS.md，所以專案若依賴 AGENTS.md，setup 會先詢問：直接寫進 AGENTS 檔，或建立一個 import 它的 CLAUDE.md，讓 Claude 繼續讀到它。選擇會記錄下來，之後沿用。詳見[專案指示檔](docs/setup.md#project-instruction-file)。

### 分派預覽

```text
/cc-feather:delegation-preview docs/specs/my-feature.md
/cc-feather:delegation-preview TICKET-12 TICKET-13
/cc-feather:delegation-preview
```

開始實作前，先看主 Agent 會如何拆分一個或多個計畫、ticket，或一段沒有計畫的工作描述：每個 claim 底下列出每一項派工與主 Agent 自己保留的部分，附上角色、model、effort 與值的來源（任務、session、已儲存或預設）。計畫與 claim 依[上方規則](#分派與預設模型)辨識，預覽會列出採用的 ticket。一段簡短說明哪些可平行、哪些要等待。計畫審查、程式碼審查與結果驗證的角色只在最後列一次，附上計畫數、claim 數與各步驟何時停下（連續兩次自動呼叫沒通過，一次不中斷的完成過程中每個 claim 最多六次，重新打開的 claim 與經你同意的重大偏離會再增加呼叫）；沒有計畫的工作會標示不在這個流程內；`off` 時會註明不執行自動流程，但仍可明確要求審查。也會標示未安裝的角色、cc-feather 看不到設定的自備 Explore、還不算計畫的輸入、提到自己的 ticket 或 claim 卻找不到，或列出的 claim 與 ticket 不一致的計畫、沒有自己驗收條件的 claim、在 `auto` 下已有 claim 實作但這個 session 沒有計畫審查紀錄的計畫（主 Agent 會問是否先補計畫審查）、在 `auto` 下需要先有審查過計畫的未計畫安全邊界變更、資料遷移或不可逆操作，以及需要先探索才能判斷的工作。不帶參數時預覽目前討論中的計畫；沒有或有多個候選時會詢問。

預覽是唯讀的：由主 Agent 自己產生，不派出任何子 Agent、不啟動審查、不佔審查次數、不寫入任何檔案。只能透過這個指令執行，在對話中提出要求不會觸發。它顯示目前已生效的設定，包含 session 的 `auto-on`／`auto-off`；想試別的 model 或 effort，請先用 `/cc-feather:model` 設定再重新預覽。預覽只在產生它的 session 中作為派工依據：在該 session 接著實作時，主 Agent 依預覽派工，並逐項回報差異與原因。其他 session 產生的預覽只供參考；在那裡派工可以與它不同，不會當作差異回報。model 與 effort 顯示的是設定值，不代表已確認的實際執行。這個指令隨 plugin 提供，plugin 更新後只要開新 session，不需要執行 setup update。詳見[預覽流程](skills/delegation/references/preview.md)。

### Explore 的成本控制

內建 Explore 會繼承主模型；只新增 plugin scout 無法防止它被呼叫。Setup 因此部署**真正名為 Explore 的原生角色**，明確寫入 sonnet/low。若你已有名為 Explore 的 agent，它本身就已取代內建 Explore：setup 不安裝自己的 Explore、不動你的檔案，並提醒它的 model 不由 cc-feather 管理（沒寫 `model` 就會使用主模型）。移除你的 Explore 後，setup update 會重新安裝 cc-feather 的版本。

內建 general-purpose 與 Plan 同樣使用主模型，且無法以同樣方式取代；因此分派規則要求主 Agent 只派給 cc-feather 角色，除非你指定使用內建 agent。

儲存值不是實際執行證據：CLI／managed／巢狀專案定義、模型 force 變數、provider allowlist 或單次參數可能影響模型。Setup 後用新 session，執行探索時以 `/tasks` 核對實際 model／effort。模型選擇降低的是意外使用昂貴模型的成本，不保證 token 數下降。參考 [Claude subagents](https://code.claude.com/docs/en/sub-agents)。

## 交接相容性

```text
/cc-feather:handoff 保存目前工作
/cc-feather:handoff 列出目前交接
/cc-feather:handoff 讀取登入功能交接
/cc-feather:handoff 接續登入功能
/cc-feather:handoff 搜尋提到登入的完成紀錄
/cc-feather:handoff-list
/cc-feather:handoff-save login
/cc-feather:handoff-resume login
```

沿用 [codex-feather](https://github.com/xenciscbc/codex-feather) 的 `.feather/handoffs/<work>.md`、`history.md` 與 `archive/<batch>.md`。讀取不接續執行；接續核對來源後繼續已授權工作。完成自動歸檔，失敗保留可重試資料；清除與封存需要明確範圍。來源基準只涵蓋選定檔案，不代表測試通過。明確指定 Claude memory 才做外部記憶唯讀查找。

Claude 與 Codex 需使用同一個專案目錄並協調單一寫入者；無跨 session 交易鎖或 worktree 自動同步。交接工具依原有規則處理 Git 忽略與使用者追蹤選擇。

## 更新、移除與驗證

Plugin 更新只更新套件，需另跑 setup update 更新選定的已部署項目，完成後開新 session，因為角色與指引在 session 開始時載入。0.17.0 改了 reviewer 與 analyst 的角色定義和自動審查指引，所以每個裝有分派元件的範圍都要跑 setup update，再開新 session；在那之前，`auto` 與 `off` 下 check 都會回報來自較舊範本的角色，`model`、`review` 與 session export 也會要求先做 setup update。此外，較早版本的安裝在更新前仍保留舊的指引格式，check 也會提醒分派指引來自較舊的範本。移除 plugin 不會自動刪除外部角色／政策，請先移除想清理的 setup scope。使用者修改過的管理檔會保留為衝突，交接紀錄不刪除。

```text
/cc-feather:setup 更新目前專案已安裝的角色與指引，保留模型與審查模式
/cc-feather:setup 移除目前專案由 cc-feather 管理的角色與指引
```

若先前安裝在 user 範圍，請明確指定更新／移除使用者範圍。移除角色與指引後，再透過 Claude 的 plugin 管理介面解除安裝套件。

[交接相容性驗證](docs/compatibility.md)記錄原有測試；新增 setup/model 的測試與限制見[設定驗證](docs/setup-validation.md)。設定與政策檔案檢查不等於已驗證真實 Claude 派工。計畫審查輪數與派工條件是模型指引，沒有 hook 強制計數；本套件不以設定成功宣稱 live model 已確認。

## Agent 名稱與舊版升級

原生名稱直接使用 `scout`、`analyst`、`mech-executor`、`executor`、`security-executor`、`verifier`、`reviewer`、`Explore`，不再有 `feather-` 前綴。

若已有其他 agent 使用同樣的名稱（即使位於不同檔名或子目錄），setup 會把 Explore 以外的角色都加上 `cc-` 前綴安裝（例如 `cc-scout`），並在分派規則中列出實際名稱；之後一直沿用前綴。其他 agent 的檔案不會被覆蓋或接管。Explore 維持原名；已有自己的 Explore 時直接沿用你的。`cc-` 名稱本身也衝突時，仍會保留檔案並請使用者決定。跨 user/project 範圍的同名角色依 Claude 優先序生效，需一併核對適用範圍。

舊版已管理的 `feather-*` 角色請執行 `/cc-feather:setup 更新目前專案的角色與指引`（user 安裝請指定使用者範圍）。Update 會預覽更名、保留 model／effort 及審查模式，只有完整且未被修改的舊角色才遷移；新名稱已被占用就停止。完成後開新 session。Model、永久審查開關與 session 匯出需先完成遷移；也可直接移除完整的舊版管理安裝。

## 致謝

代理角色與協作方式參考了 Nanako0129 的 [pilotfish](https://github.com/Nanako0129/pilotfish)。
