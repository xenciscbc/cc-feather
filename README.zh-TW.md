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
| `/cc-feather:handoff-history [日期、日期..日期、工作標題或關鍵字] [sealed] [筆數或 all]` | 瀏覽完成歷史（唯讀）。不帶參數時，由新到舊列出最近 10 筆完成紀錄的編號標題；參數可依完成日期、含頭尾的日期區間、工作標題或關鍵字篩選，`sealed` 納入已封存的歷史，結尾的數字或 `all` 決定顯示筆數。回覆編號即可看那幾筆的全文。組合條件請用自己的話請 `/cc-feather:handoff` 查詢 |
| `/cc-feather:handoff-save [工作]` | 保存指定工作；省略時保存目前工作 |
| `/cc-feather:handoff-resume [工作]` | 接續指定工作或唯一未完成的工作；有多項時詢問 |
| `/cc-feather:handoff-tidy [工作名稱或 all]` | 整理既有的交接紀錄，只能由你執行。不帶參數時詢問模式：Proposal（只讀紀錄，建議下一項工作，並指出可合併、過時或不完整的紀錄）、Full check（先說明成本並等你確認，再拿每筆紀錄對照目前專案）或 Selected check（核對你指定的工作），你也可以用自己的話描述想做什麼；帶工作名稱直接做 Selected check，帶 `all` 做 Full check。檢查唯讀，不執行專案程式碼。它只提出建議：合併、搬移項目與更新進度都在你確認後才寫入，也不會授權它建議的工作或開始交接維護 |
| `/cc-feather:setup` | 先查狀態，分別或一起管理 handoff 自動維護規則、agent 分派規則與角色安裝，以及選用的 Checkout lease 規則 |
| `/cc-feather:delegation` | 按需載入主 Agent 的派工、審查、驗收與復原流程 |
| `/cc-feather:delegation-preview [計畫、ticket 或工作]` | 預覽工作會如何分派，不實際派工；見[分派預覽](#分派預覽) |
| `/cc-feather:adversarial-review <攻擊範圍> [路徑或 commit 範圍] [可拋棄目標]` | 執行你要求的對抗式審查，兩種模式都可用；見[安全關鍵工作](#安全關鍵工作) |
| `/cc-feather:model` | 查看、設定角色 model／effort，區分單次、session 與永久選擇 |
| `/cc-feather:auto-on` | 開啟依計畫施工的自動計畫審查、程式碼審查、結果驗證，以及安全關鍵 claim 的對抗式審查，也就是自動流程，除非你為某份計畫選了其他等級，它都以[審查等級](#審查等級) `standard` 執行；主 Agent 之後可不經詢問，在通過前 commit 這類工作、推送到它為此工作建立的 branch 並開 pull request，但合併到預設 branch、release、回報完成與 ticket 完成仍需兩項通過（安全關鍵 claim 還要加上 HELD）或你的接受並合併決定 |
| `/cc-feather:auto-off` | 關閉自動審查 |
| `/cc-feather:stop-threshold <2–10 或 default> [範圍]` | 設定自動審查的[停止門檻](#停止門檻)：只用於這個 session（不帶範圍或 `session`），或儲存在 `project` 或 `user` 範圍 |
| `/cc-feather:related-tests <on、off 或 default> [範圍]` | 開啟或關閉[相關測試驗收](#相關測試驗收)：只用於這個 session（不帶範圍或 `session`），或儲存在 `project` 或 `user` 範圍 |
| `/cc-feather:auto-land <on、off 或 default> [範圍]` | 開啟或關閉[自動合併](#自動合併)：只用於這個 session（不帶範圍或 `session`），或儲存在 `project` 或 `user` 範圍 |
| `/cc-feather:test-speedup [測試路徑或範圍]` | 找出讓測試（或你指定的部分）變快、又不削弱驗證內容的方法；只能由你執行，不改任何檔案。先做靜態分析，列出可能耗盡記憶體或時間的既有測試，經你同意才量測；見[參考文件](docs/reference.zh-TW.md#設計與測試檢查) |
| `/cc-feather:overdesign-check [檔案、目錄、spec、diff 範圍或規則文字]` | 檢查剛才討論的提案，或你指定的對象，是否有過度設計：防範只有專案自己的程式碼才會造成的狀態、為已不存在的格式或 token 保留相容、只有一個使用者的設定，以及重疊的防禦。只能由你執行，不改任何檔案；每一項都附權衡與建議，舊格式相容只有在有證據時才判定為不需要，否則會問你；見[參考文件](docs/reference.zh-TW.md#設計與測試檢查) |
| `/cc-feather:leases` | 取得、續期、接手、歸還與列出 Checkout lease；主 Agent 維護 lease 時載入。見 [Checkout lease](#checkout-lease) |
| `/cc-feather:worktrees` | 列出這個儲存庫的每個 checkout，以及它的 Checkout lease、Git worktree lock 與留在其中的工作；只能由你執行。它不是唯讀：持有中的 lease 所在 worktree 沒有 lock 時會重新上鎖，並移除 Git 已不再登記其 checkout 的 lease |
| `/cc-feather:merge-upstream [計畫名稱]` | 遠端預設 branch 移動後（例如另一份計畫先合併了），把它帶進一份在 auto 下等待合併的計畫；只能由你執行。你同意後，主 Agent 在本機把它 merge 進計畫的 branch，絕不 rebase；這次 merge 的整合報告（Integration report）要經過計畫審查與你的核可，被它重新開啟的審查會再跑一次，之後這份計畫只在你親自下令或接受並合併時才合併，絕不經由自動合併。見[合併上游](docs/reference.zh-TW.md#合併上游) |

交接指令在 plugin 安裝後即可使用。Setup 可只裝 handoff 自動維護規則、只裝 agent 分派（規則＋角色），或兩者都裝。例如：

```text
/cc-feather:setup 在目前專案只安裝 agent 分派規則與角色
/cc-feather:model 顯示目前專案的角色模型設定
/cc-feather:model 將目前專案 executor 的 effort 永久改為 high
```

Setup 先查現有狀態，再補問未指定的操作、項目與範圍；寫入前會預覽，檢查衝突、備份並管理擁有權；不改主模型、並行數、settings.json 或既有交接資料。永久 model 修改寫入原生角色檔，setup 更新保留已選設定。單次指定不會修改永久設定。詳見[設定與生命週期](docs/setup.md)。

## Setup：先查狀態，再選擇項目

直接輸入 `/cc-feather:setup`，會先查目前專案及使用者範圍的安裝狀態，列出各項是否已安裝、是否衝突或需要遷移，再詢問要安裝、更新、移除或只查看哪一項，以及操作範圍。若已指定範圍，只檢查該範圍；已說清楚的選擇不會重問。

| 可選項目 | 安裝內容 | 移除後 |
| --- | --- | --- |
| handoff | 指示檔中獨立的自動維護規則 | 只移除提醒；交接紀錄與 plugin 的 handoff 指令仍保留 |
| agent 分派（delegation） | 獨立分派規則＋九個原生 agent；自動計畫審查預設關閉 | 移除完整的受管理角色及分派規則，保留 handoff 規則 |
| leases | 指示檔中的 Checkout lease 規則；只有你指名選擇時才安裝 | 只移除規則；lease 紀錄與 Git worktree lock 仍保留 |
| 兩者（both） | handoff 與 agent 分派；不含 leases | 依所選操作一起處理，仍保留交接資料與其他使用者設定 |

可直接指定，不必走逐項詢問：

```text
/cc-feather:setup 在目前專案只安裝 handoff 自動維護規則
/cc-feather:setup 在目前專案只安裝 agent 分派規則與角色
/cc-feather:setup 在目前專案兩者都安裝
/cc-feather:setup 在使用者範圍安裝 Checkout lease 規則
/cc-feather:setup 只更新目前專案的 handoff 規則
/cc-feather:setup 只移除目前專案的 agent 分派，保留 handoff
/cc-feather:setup 查看使用者範圍的安裝狀態
```

「兩者都安裝」只補上尚未安裝的項目；「更新兩者」只更新已安裝項目；「移除兩者」只移除已安裝項目。已存在或不存在的另一項不會因此被重設。

各項在該範圍的指示檔中各有獨立的管理區塊，安裝狀態在各範圍的 `cc-feather/state.json` 分項保存。handoff 規則不會自行建立新紀錄：仍需使用者要求建立或接續後，才在里程碑、受阻與完成時維護同一份紀錄。只查看／列出不啟用維護。

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
| 安全關鍵實作 | security-executor | opus | high |
| 實作後驗證 | verifier | opus | high |
| 實作後程式碼審查 | reviewer | opus | high |
| 對抗式審查 | adversary | opus | high |

| 角色 | 何時使用 | 產出與權限 |
| --- | --- | --- |
| scout | 範圍明確的事實查找，例如定位定義、設定或引用 | 唯讀；回報檔案位置與證據，不做複雜因果分析。 |
| Explore | 尚不清楚程式結構，需要較廣的模組、入口、呼叫關係探索 | 唯讀；建立理解程式的地圖，深入診斷交給 analyst。 |
| analyst | 根因／影響分析、安全問題查找、實作前計畫審查 | 唯讀；回報證據、推論與建議；計畫審查回覆 READY／REVISE。 |
| mech-executor | 規則、範圍與結果已明確的重複修改 | 可修改指定檔案；按完整規格執行，例如批次改名 |
| executor | 需要局部設計與工程判斷的功能或修正 | 可修改指定檔案並驗證，遇到架構或需求缺口交回主 Agent |
| security-executor | 影響授權、秘密資料、密碼學或信任邊界的實作 | 可修改指定檔案；驗證正常行為及濫用／拒絕案例 |
| verifier | 獨立確認完成的實作是否符合明確的 claim | 執行檢查與反例，不修改檔案；回覆 CONFIRMED／REFUTED／INCONCLUSIVE。它只在主 Agent 的 brief 說它可以時才執行儲存庫的程式碼。 |
| reviewer | 獨立審查實作某個 claim 的程式碼 | 自行比對 base revision 與受審 commit，並讀取主 Agent 列出的未提交檔案，只跑 brief 指定的 lint 與型別檢查，不修改檔案也不跑測試；回覆 APPROVED／CHANGES_REQUESTED／INCONCLUSIVE。它只在主 Agent 的 brief 說它可以時才執行儲存庫的程式碼。 |
| adversary | 嘗試攻破一個安全關鍵 claim，只針對 brief 指定的可拋棄目標 | 只有 Read、Glob、Grep、Bash，絕不修復程式碼；回覆 HELD／BROKEN／INCONCLUSIVE。只有 brief 把某個專案檔列為 fixture 並附上重設方式時才會改動它，且絕不在受把關的呼叫中改動。這些安全限制（這條 fixture 規則、只用 brief 指定、使用合成資料的可拋棄目標，不連外部主機）是給模型的指示，不是沙箱：Bash 仍可連網與寫檔，主 Agent 會在每次呼叫前後比對工作區。它只在主 Agent 的 brief 說它可以時才執行儲存庫的程式碼。 |

主 Agent 保留需求理解、決策、整合與最後驗收。小型或脈絡高度耦合的工作直接處理；獨立子任務才分派，明確指定範圍、檔案 ownership 與完成條件。子 Agent 都是 leaf，不再往下分派，也不維護交接或進度紀錄，改由主 Agent 依其回報記錄。

每個欄位獨立套用優先序：**該次任務明確指定 > 適用的 session 指定 > 已儲存角色設定 > 套件預設**。例如「用 Sonnet 審查計畫」仍使用 analyst 職責，model 改為 Sonnet，未指定 effort 則保留 analyst 的 high。指定值無法原生套用時先說明，不暗中替換或只在 prompt 假裝設定成功。

安全分析由唯讀 analyst 做；安全關鍵變更（Security-critical change）的實作交給 security-executor。

自動審查預設關閉，用[開關](#自動審查開關)開啟或關閉。開啟後只涵蓋**依計畫施工的工作**：依你同意的計畫、spec、ticket 或對話中的計畫進行的工作。下面的步驟就是自動流程，以[審查等級](#審查等級) `standard` 執行，這是計畫在你沒有另選等級時的等級。

| 步驟 | 時機 | 角色 | 通過條件 |
| --- | --- | --- | --- |
| 計畫審查 | 施工前 | analyst | READY |
| 程式碼審查 | 主 Agent 的主要驗收通過後，或因你說明的限制涵蓋它而記為未執行時 | reviewer，自行取得 diff | APPROVED |
| 結果驗證 | APPROVED 之後 | verifier | CONFIRMED |
| 對抗式審查 | 安全關鍵 claim：在 auto 下，最終檢查在最後的 commit 上通過後，最後做一次；在 `off` 下，在同一個 commit 拿到 APPROVED 與 CONFIRMED 之後 | adversary | HELD |

重點如下；規則寫在分派流程中，[參考文件](docs/reference.zh-TW.md#自動審查)說明每條規則的用途，並連到寫明它的流程：

- **沒有計畫的工作**不自動審查；但做出安全關鍵變更、資料遷移或不可逆操作之前，要先有一份經過審查、由你核准的書面計畫。
- **計畫就是你指名的東西。**要求主 Agent 實作時指名計畫、spec 或 ticket，就代表你同意它，而你指名的內容決定它的 claim：spec 是一個 claim，除非它自己列了 claim；一份 spec 的 ticket 是一個計畫，每張未完成的 ticket 一個 claim；單一 ticket 本身就是計畫和 claim。claim 的實作者與審查者讀的是 claim 本身和它引用的 spec 段落，不是整份 spec。
- **依 claim 審查的時機：**在 auto 下，每個 claim 一實作完並 commit，就做程式碼審查、再做結果驗證；依賴另一個 claim 的 claim，要等那個 claim 拿到有效的 APPROVED 與 CONFIRMED 才開始。之後計畫中另一個 claim 改到這個 claim 的檔案時，只要改動落在那個 claim 自己通過的審查所判斷的範圍內，這些通過結果就維持不變。
- **擋住 claim 的只有：**驗收沒有照所寫的達成、有 failing test 或重現步驟證明既有行為壞了、引入安全問題或資料遺失，或偏離計畫。其他問題都記進這份工作的後續紀錄，由你決定之後要不要開計畫修。
- **次數上限：**每個步驟連續沒通過的自動呼叫達到[停止門檻](#停止門檻)（預設 2）就停下來等你。次數只屬於同一個 session；在 auto 下，通過結果、對抗式審查結果與你的決定會透過 `.feather/dispatch/` 下這份計畫的派工紀錄跨 session 延續，主 Agent 照紀錄所寫的內容採信。
- **最終檢查與合併：**在 auto 下，主 Agent 可以在通過前 commit claim、推送到它為這份工作建立的 branch 並開 pull request。合併前，主 Agent 會在要合併的 commit 上重跑每個 claim 的主要驗收，除非你選了最終檢查範圍 `related`，否則也會跑計畫的整體驗收；失敗時由造成失敗的 claim 或一個修正用的 claim 修正。在 auto 下，主 Agent 接著只在計畫結束時問你一次，列出每個 claim 的通過結果、缺少的部分，以及這套流程沒有檢查的事。主 Agent 在對話中提出這個決定，不用提問工具並結束它的回合，計畫開始實作後它停下來等你回答的每個問題都是如此，讓你可以用 `/clear` 或新的 session 離開，不必多一次模型呼叫。審查等級的提問與 READY 之後的提問在實作開始前提出，仍使用提問工具。合併到預設 branch、release、回報完成與 ticket 完成，都要等兩項通過（安全關鍵 claim 還要 HELD）或你的接受並合併決定。
- **最終檢查範圍：**在 auto 下，計畫審查會為計畫建議 `full` 或 `related` 並說明理由，主 Agent 會在 READY 之後、與資源風險提議同一次的提問中問你，附上計畫審查的建議與它自己的建議；之後的計畫審查在建議與上次提問所依據的建議不同，或主 Agent 無法確定是否不同時，會再問你。`full` 會執行計畫的整體驗收，也重跑每個 claim 的主要驗收；`related` 只重跑每個 claim 的主要驗收。在 `full` 下，claim 主要驗收中整體驗收自己的執行已明確跑過、且工具與條件都相同的指令，不會再跑第二次；主 Agent 無法確立已涵蓋的指令會另外執行，計畫結束時的決定與完成報告會列出被涵蓋的 claim。是否涵蓋是依指令與執行的輸出判斷，而輸出由儲存庫的程式碼掌控。只有你自己對主 Agent 所問範圍問題的回答能設定範圍，沒有這個提問時你表示的選擇不會設定範圍；你要求改變範圍時，主 Agent 會問你一個新的範圍問題。主 Agent 在問每個範圍問題之前，會先在計畫的派工紀錄中把它標為待回答，在你的回答記錄下來之前範圍是 `full`，所以因 context 壓縮而遺失的回答只會擴大最終檢查。release 或 tag 時，它的 commit 上若已有有效的 `full` 通過就直接沿用而不問；否則主 Agent 會針對那個 commit 問你要執行 `full`，還是以那裡 `related` 的執行打 tag（這會省略整體驗收），在你的回答記錄下來之前，release 執行 `full`。你的回答只適用於那個 commit，不會改變計畫的範圍，也不是要求打 tag 的指示；那個 commit 上的失敗不會因此免除，tag 的報告會寫出這次 release 用的是 `related`。兩種範圍會跑相同檢查時不會問你。計畫結束時的決定與完成報告會寫出最終檢查執行時的範圍。在用 Git 追蹤 `.feather/test-suites.md` 測試套件目錄的專案中，兩種範圍也都會執行每個 gates 含 `landing` 的套件，如 [setup 文件](docs/setup.md#test-suite-catalogue)所述。
- **明確要求**任何審查，兩種模式都可用，只跑你要求的部分，不占自動次數。
- **成本：**在預設停止門檻下，一次不中斷的過程中，每個 claim 最多 6 次自動呼叫，安全關鍵 claim 最多 8 次；每次重新打開的 claim、最終檢查的修正或核准的偏離都會再增加呼叫；其他門檻的公式與降低成本的方法見參考文件。

完整規則見[計畫審查](skills/delegation/references/plan-review.md)、[程式碼審查](skills/delegation/references/code-review.md)、[結果驗證](skills/delegation/references/outcome-verification.md)與[對抗式審查](skills/delegation/references/adversarial-review.md)程序；用語定義見 [CONTEXT.md](CONTEXT.md)。

### 審查等級

在 auto 下，計畫的第一個 claim 實作之前，主 Agent 會為這份計畫建議一個審查等級（Review level）並附上一行理由，請你選擇，建議的選項排在第一個。你自己指定的等級，例如「用 light 實作 ticket 03」，就是你的選擇，不會再問；寫在 ticket 或 spec 裡的等級只作為建議的參考。

- `standard` 執行上面的自動流程。
- `light` 對這份計畫關閉自動審查，並加上三件主 Agent 自行做的事：claim 實作完後，請 reviewer 審查這個 claim 的程式碼，收到 CHANGES_REQUESTED 就修正發現的問題再請它審查，直到審查通過或在[停止門檻](#停止門檻)停下；執行 claim 驗收的每一項並回報每項實際觀察到的結果，沒執行的項目回報為未執行；之後在對話中停下，不用提問，列出審查結論、驗收結果、未解決的發現與剩下的工作，包括合併。
- `off` 對這份計畫關閉自動審查。

主 Agent 只在計畫只有一個 claim、原因已知且範圍小、驗收能直接顯示結果、不是安全關鍵、不遷移資料、沒有不可逆操作、沒有可預見的資源風險，也不改共用的測試支援或建置設定時，才建議 `light`。`light` 放棄的與 `off` 相同：計畫審查、結果驗證、作為記錄關卡的最終檢查、派工紀錄、自動合併，以及把關；`light` 下的 claim 只有在進行中的交接記錄它時才受把關。`light` 的計畫只透過進行中的交接跨 session 延續，它的 ticket 在你接受或說它完成之前都維持未完成，而且只在你下令時才合併。`off` 保有的每條規則仍然適用，包括安全關鍵工作的安全分析與交給 security-executor。主 Agent 絕不自行調高或調低等級：在這個 session 還不知道你的選擇時，例如 context 壓縮後沒有進行中的交接記錄它，等級就是 `standard`；`light` 的計畫若發現需要安全關鍵變更或出現重大偏離，主 Agent 會停下，由你重新選擇它的等級。規則是審查狀態規則的 Review level，[參考文件](docs/reference.zh-TW.md#審查等級)說明原因。

### 安全關鍵工作

```text
/cc-feather:adversarial-review 檢查 src/auth 的 session token 驗證，使用計畫指定的測試伺服器
/cc-feather:adversarial-review 密碼重設流程 HEAD~3..HEAD
```

安全關鍵 claim 會改變信任邊界上的安全保證或某個安全控制，例如驗證、授權、session、憑證、密碼學或輸入驗證；主 Agent 依它做了什麼來判斷，而不是看關鍵字。它由 security-executor 實作，`off` 下也一樣。在 `auto` 下，它的計畫先做一次唯讀的安全分析，分析結果寫成 claim 驗收中的安全不變式，接著才做計畫審查。adversary 會對可拋棄的目標嘗試攻破這個 claim，回覆 HELD、BROKEN 或 INCONCLUSIVE。在 `auto` 下，它只在最終檢查於最終 commit 通過後，在那個 commit 執行一次；BROKEN 會被記錄下來，列在計畫結束時給你決定，而不是在計畫中修正。在 `off` 下，它在同一個 commit 拿到有效的 APPROVED 與 CONFIRMED 之後執行，BROKEN 要回去修。變更之前就存在的漏洞會成為你 tracker 裡的另一項工作，攻擊細節不寫進公開紀錄。`/cc-feather:adversarial-review` 隨時可以照你的要求執行對抗式審查，兩種模式都可用。adversary 的限制是給模型的指示：只有你的權限設定、hooks、Claude Code sandbox 或隔離環境能強制執行。詳見參考文件的[安全關鍵工作](docs/reference.zh-TW.md#安全關鍵工作)。

### 儲存庫安全

**分派假設儲存庫是受信任的，審查會在這台機器上執行它的程式碼。說明變更從哪裡來（例如它是別人的 pull request、branch 或 patch）已經不會阻止這件事：要阻止，請在你自己的訊息中說程式碼不得執行，或指出哪些不得執行。cc-feather 不提供在你信任儲存庫之前檢查它的功能，所以要不要信任一個儲存庫（例如下載或複製別人的儲存庫之後）由你決定。**

主 Agent 與角色用一般的檔案工具與一般的 Git 指令讀取儲存庫；沒有任何審查能隔離或偵測有惡意的儲存庫內容。審查只保留讓結果正確的檢查：`HEAD` 是該次呼叫判斷的 commit，claim 依賴的內容在呼叫前後都沒有未提交或未追蹤的變動，commit 只包含 claim 的檔案。你說明的限制（在你自己的訊息中，或在你對主 Agent 提問的回答中）在整個 session 有效，涵蓋它指名的每個後續呼叫（包括最終檢查），直到你自己的訊息或你的回答解除它；儲存庫中的任何內容、你的回答以外的工具輸出或紀錄都不能提出或解除限制。這些規則是給模型的指示，不是 sandbox；它們寫在分派流程中，[參考文件](docs/reference.zh-TW.md#儲存庫安全)加以說明。詳見 [ADR 0016](docs/adr/0016-delegation-trusts-the-repository.md)。

剩下的是你要承擔的風險：

- 儲存庫的內容可能透過它的 `CLAUDE.md`、註解、commit 訊息，或主 Agent 與角色讀到的任何東西引導它們：角色可能被引導把變更造成的安全問題說成既有問題或只是推測，主 Agent 可能被引導去執行限制涵蓋的程式碼，因為限制本身也只是給主 Agent 的指示。
- 審查與最終檢查會在這台機器上執行儲存庫的程式碼，而主 Agent 與角色的 Git 指令（每次呼叫前後的 `git status`、角色的讀取，以及 `git add`、commit 與 push）會執行儲存庫的 Git 設定、attributes 與 hooks 選定的程式，包括追蹤目錄中的 hook 以及 `git status` 執行的 filter，不論是否有限制生效。這些程式碼能改動你能改動的任何東西，包括你自己的 Git 設定、其他 worktree 與 Feather 自己的紀錄。
- 限制管的是審查與最終檢查，不是實作：executor 與 security-executor 實作時可能執行儲存庫的程式碼，修正別人的變更時也一樣。
- cc-feather 中沒有任何東西會在程式碼執行前先問你；剩下的只有 Claude Code 的資料夾信任與你的權限設定。
- 你指定過的隔離環境，在一般性的限制下仍可使用，除非限制另有說明；如果那個環境存有秘密資料（例如 CI runner），程式碼就會在那裡執行。
- 被忽略的檔案，以及標為 assume-unchanged 或 skip-worktree 的檔案，不在工作區檢查的範圍內，所以這類檔案可能影響審查或最終檢查。
- Claude Code 在專案中開始 session 時會載入專案的 `CLAUDE.md` 與 `.claude` 設定，並執行那些設定中的 hook，所以儲存庫在任何審查開始前就可能有所動作。
- 停止執行的陳述只在這個 session 有效，被 context compaction 遺失時也就跟著遺失；新的 session（包括接續 handoff 的 session）不帶有它們。

### 自動審查開關

```text
/cc-feather:auto-on
/cc-feather:auto-off
/cc-feather:auto-on project
/cc-feather:auto-off user
```

不帶參數（或加 `session`）只影響目前 session；加 `project` 或 `user` 則永久儲存至該範圍既有的 setup 安裝。保留 Claude plugin 的 `cc-feather:` 命名空間，指令名稱不再重複 `feather-`。

預設 `off` 不自動觸發；開啟後的 `auto` 以[審查等級](#審查等級) `standard` 對依計畫施工的工作執行自動流程（除非你為某份計畫選了其他等級），並在這個等級下讓主 Agent 不經詢問，在 claim 通過前先 commit、推到它為這項工作建立的 branch，以及開 PR 列出尚未驗收的 claim；進入預設 branch、release、回報完成與把 ticket 設成完成，仍要等兩關都通過（安全關鍵 claim 還要加上 HELD），或你明確決定「接受並合併」（見[參考文件](docs/reference.zh-TW.md#自動審查)的 Commit 條件與你的決定）；兩者都接受明確要求的審查。永久設定不會取消另行指定的單次／session 偏好。可用 setup 查詢已儲存模式；更新保留永久選擇，切換不會讓既有計畫或 claim 的各步驟次數歸零。

永久模式儲存位置如下；請透過指令修改，避免手動編輯管理區塊造成擁有權衝突。

| 範圍 | 載入給 Claude 的政策 | 同步管理狀態 |
| --- | --- | --- |
| project | `<專案>/CLAUDE.md`、`.claude/CLAUDE.md` 或 AGENTS.md（見下方） | `<專案>/.claude/cc-feather/state.json` |
| user | `<Claude 設定目錄>/CLAUDE.md` | `<Claude 設定目錄>/cc-feather/state.json` |

Claude 設定目錄預設是 `~/.claude`，可由 `CLAUDE_CONFIG_DIR` 指定。`auto` 時分派區塊包含自動審查規則，`off` 時整段移除，主 Agent 與子 Agent 都不會載入。專案範圍的 `off` 會保留一行「此專案關閉自動計畫審查」的說明，因此覆蓋使用者範圍的 `auto`：任務／session 選擇優先，其次是專案指示，最後是使用者指示。較早版本以 `off` 安裝的專案，要到下次執行 review 或 setup update 才加入這一行。較早版本的安裝保留 `Automatic plan review mode:` 那行，執行 setup update 後改為新格式。永久開關需要先安裝該範圍的 agent 分派；只有 handoff 規則不夠；新 session 載入已儲存模式。

project 範圍會寫進既有的 CLAUDE.md，沒有的話寫進 `.claude/CLAUDE.md`。Claude Code 只在沒有任何 CLAUDE 檔時才讀 AGENTS.md，所以專案若依賴 AGENTS.md，setup 會先詢問：直接寫進 AGENTS 檔，或建立一個 import 它的 CLAUDE.md，讓 Claude 繼續讀到它。選擇會記錄下來，之後沿用。詳見[專案指示檔](docs/setup.md#project-instruction-file)。

### 停止門檻

停止門檻是自動流程的一個步驟連續幾次自動呼叫沒通過就停下：所有步驟共用一個 2 到 10 的數字，預設 2。

```text
/cc-feather:stop-threshold 4
/cc-feather:stop-threshold 4 project
/cc-feather:stop-threshold default user
```

不帶範圍（或用 `session`）只用於這個 session，不寫入任何檔案；`project` 或 `user` 會存進該範圍既有的分派安裝。主 Agent 依序採用你在這個任務或 session 的選擇、專案儲存的值、使用者儲存的值，最後才是 2，絕不自行更改。變更門檻絕不會改變次數。門檻越高，流程不問你就能重試越久，成本也比門檻增加得更快。詳見參考文件的[停止門檻](docs/reference.zh-TW.md#停止門檻)。

### 相關測試驗收

相關測試驗收（Related-test acceptance）改變主 Agent 在 spec、ticket 或計畫中撰寫 Claim 驗收的方式：開啟時，驗收列出與變更相關的測試模組，而不是完整測試；計畫的整體驗收仍是完整測試，由最終檢查執行。預設關閉。

```text
/cc-feather:related-tests on
/cc-feather:related-tests off project
/cc-feather:related-tests default user
```

不帶範圍（或加 `session`）時只用於這個 session，不寫入任何檔案；加 `project` 或 `user` 時，會儲存到該範圍既有的 agent 分派安裝，它絕不會安裝 agent 分派。主 Agent 依序採用你在這個 session 的選擇、專案儲存的選擇、使用者儲存的選擇，最後才是關閉，所以專案的 `off` 會覆蓋使用者的 `on`；主 Agent 絕不自行更改。它只改變主 Agent 撰寫驗收的方式，不改變任何審查或最終檢查的執行方式；變更只適用於之後撰寫的驗收，不改動已寫好的驗收。詳見參考文件的[相關測試驗收](docs/reference.zh-TW.md#相關測試驗收)。

### 自動合併

自動合併（Auto land）是你事先給主 Agent 的常設授權：在 auto 下，計畫最後的決定裡沒有任何項目需要你決定接受並合併時，主 Agent 不再詢問，直接合併計畫。預設關閉。

```text
/cc-feather:auto-land on
/cc-feather:auto-land off project
/cc-feather:auto-land default user
```

不帶範圍（或加 `session`）時用於這個 session，不寫入任何設定檔；加 `project` 或 `user` 時，會儲存到該範圍既有的 agent 分派安裝，它絕不會安裝 agent 分派。主 Agent 依序採用你在這個 session 的選擇、專案儲存的選擇、使用者儲存的選擇，最後才是關閉，所以專案的 `off` 會覆蓋使用者的 `on`；主 Agent 絕不自行更改。session 的 `off` 也會擋住這個對話中的每個計畫：主 Agent 會把它記在每個這類計畫的 dispatch 紀錄中，之後對那個計畫而言，它排在你的 session 選擇之後、儲存的選擇之前，在恢復的 session 中與 context 壓縮之後也一樣。只有你在這個對話中親口說的話（包括你對主 Agent 提問的回答）能解除它：session 的 `on` 或 `default`、明確解除，或儲存 `on`；儲存 `off` 或 `default` 不會解除它，而且主 Agent 每次說明目前的設定時，都會指出來源是記錄下來的 `off`，以及它記錄的時間與解除方式。主 Agent 只會把最終檢查與審查判斷過的 commit 以 fast-forward 推送到預設 branch 來合併，無法這樣推送時就停下來問你；release 與 tag 仍由你決定，不推送的指示會擋住它。專案範圍的 `on` 通常會隨專案的指示檔一起 commit，所以每個載入它的 clone 都會用自己的推送權限合併。詳見參考文件的[自動合併](docs/reference.zh-TW.md#自動合併)。

### 分派預覽

```text
/cc-feather:delegation-preview docs/specs/my-feature.md
/cc-feather:delegation-preview TICKET-12 TICKET-13
/cc-feather:delegation-preview
```

開始實作前，先看主 Agent 會如何把計畫、ticket 或沒有計畫的工作拆成 claim 與分派：每個角色、model 與 effort 及其來源、哪些可以平行、各審查步驟與何時停下，以及任何會擋住工作的情況，例如缺少角色或輸入還不算計畫。預覽是唯讀的：不派出任何工作、不占審查次數、不寫入檔案，而且只在產生它的 session 中作為分派依據。詳見參考文件的[分派預覽](docs/reference.zh-TW.md#分派預覽)。

### Explore 的成本控制

內建 Explore 會繼承主模型；只新增 plugin scout 無法防止它被呼叫。Setup 因此部署**真正名為 Explore 的原生角色**，明確寫入 sonnet/low。若你已有名為 Explore 的 agent，它本身就已取代內建 Explore：setup 不安裝自己的 Explore、不動你的檔案，並提醒它的 model 不由 cc-feather 管理（沒寫 `model` 就會使用主模型）。移除你的 Explore 後，setup update 會重新安裝 cc-feather 的版本。

內建 general-purpose 與 Plan 同樣使用主模型，且無法以同樣方式取代；因此分派規則要求主 Agent 只派給 cc-feather 角色，除非你指定使用內建 agent。

儲存值不是實際執行證據：CLI／managed／巢狀專案定義、模型 force 變數、provider allowlist 或單次參數可能影響模型。Setup 後用新 session，執行探索時以 `/tasks` 核對實際 model／effort。模型選擇降低的是意外使用昂貴模型的成本，不保證 token 數下降。參考 [Claude subagents](https://code.claude.com/docs/en/sub-agents)。

## 設計取捨

cc-feather 寧可讓審查有界、可預期，也不追求什麼都檢查。下面每個選擇都刻意放棄了某些東西；連結的 ADR 記錄了原因。在 auto 下，主 Agent 在計畫結束時問你的那一次，也會列出這套流程沒有檢查的事。

- **規則是指示，不是強制。**審查流程、執行儲存庫程式碼的規則與角色限制都是給模型的指示。測試讓出貨的文字保持一致，但沒有任何 hook 或工具強制執行；真正的限制只來自你的權限設定、hooks、sandbox 或隔離環境。（[ADR 0016](docs/adr/0016-delegation-trusts-the-repository.md)）
- **審查只讀窄範圍的內容。**每次審查只判斷一個 claim，只讀 claim 本身和它引用的 spec 段落，所以不會拿 claim 沒採用的段落來判斷，也不會被無關的問題淹沒。代價是後面 claim 的審查者可能不知道前面 claim 的設計意圖；跨 ticket 的設計意圖應該寫進 spec，由計畫審查檢查每張 ticket 都引用了適用於它的部分。（[ADR 0012](docs/adr/0012-claims-are-decided-by-what-the-user-names.md)）
- **每個 claim 完成時就審查，並保留它的通過結果。**前面 claim 的問題會在後面的 claim 疊上去之前被發現，後面 claim 經過審查的改動碰到共用檔案時，也不會讓前面每個 claim 都重審。代價是前面 claim 的某個性質，如果沒有任何會重跑的驗收檢查涵蓋，就可能被改壞而最終檢查沒發現。（[ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#fixed-passes)）
- **最終檢查重跑主要驗收，不是每一項。**主 Agent 在要合併的 commit 上重跑計畫的整體檢查與每個 claim 的主要驗收，失敗只修一次，由造成失敗的 claim 或一個修正用的 claim 修，而不是重開每個 claim。其他驗收項目，以及無法重跑的檢查（例如人工檢查），不會在那裡重做。最終檢查範圍為 `related` 時（由你逐個計畫選擇），計畫的整體檢查也不會在那裡執行，所以計畫可能沒跑完整測試就合併。（[ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#the-final-check-and-fix-claims)）
- **只有安全關鍵 claim 有攻擊步驟，而且只在最後做一次。**程式碼審查讀 diff，結果驗證確認 claim 成立，兩者都不會嘗試繞過它；所以只有安全關鍵 claim 會在計畫審查前做安全分析，並做對抗式審查。在 auto 下，對抗式審查只在最終 commit 做一次，而不是每次修正後都做。代價是它攻擊的 commit 沒有被該 claim 自己的程式碼審查與結果驗證整體判斷過，BROKEN 會記錄下來交給你決定，而不是在計畫中修正，安全關鍵的修正用 claim 也不做對抗式審查。（[ADR 0009](docs/adr/0009-security-critical-claims-get-an-adversarial-review.md)、[ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#adversarial-review-at-the-final-commit)）
- **只有驗收需要的東西擋住完成，安全除外。**驗收範圍外的正確性問題，或只是推測的 regression，會記下來留給之後的計畫，而不是一輪接一輪地修；變更引入的安全問題或資料遺失仍然會擋。（[ADR 0013](docs/adr/0013-only-what-a-claims-acceptance-needs-holds-its-completion.md)）
- **有上限的次數，而不是重試到通過為止。**每個步驟到停止門檻就停下等你，所以主 Agent 和審查者意見不合時，會交給你決定，而不是繼續消耗呼叫。（[ADR 0004](docs/adr/0004-consecutive-failure-review-budget.md)、[ADR 0010](docs/adr/0010-the-stop-threshold-is-one-configurable-number.md)）
- **次數只屬於自己的 session；審查狀態透過照寫採信的紀錄跨 session。**接續的 session 重新計數。在 auto 下，通過結果、對抗式審查結果、最終檢查的執行紀錄與你的決定透過計畫的派工紀錄延續，主 Agent 照紀錄所寫的內容採信，所以改動紀錄就會改變主 Agent 的認知。記錄下來的最終檢查通過，只在 `HEAD` 仍是它執行時的 commit、工作區與每個 claim 的閱讀範圍都沒有變動，且它的範圍仍涵蓋所需時才沿用；否則主 Agent 重跑最終檢查，而執行之後的環境變動（例如工具升級）不會被偵測到。在 `off` 下，接續的 session 會重跑最終檢查，先前 session 通過的 claim 在合併前會再審一次。（[ADR 0002](docs/adr/0002-session-scoped-review-counts.md)、[ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#the-dispatch-record)）
- **早點 commit，合併時只決定一次。**主 Agent 可以在通過前 commit 並開 pull request，讓環境被回收時不會遺失工作，每次審查也都判斷固定的 commit；合併、release 與完成仍要等通過或你的接受並合併決定，而在 auto 下這個決定只在計畫結束時做一次。（[ADR 0007](docs/adr/0007-commit-before-acceptance.md)、[ADR 0008](docs/adr/0008-repository-authority-acceptance-and-gate-lifetime.md)、[ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#the-decision-at-the-end)）
- **分派信任儲存庫。**為讀取有惡意的儲存庫而設的規則讓每次審查都付出代價，卻什麼也隔離不了，因為審查會執行儲存庫的程式碼，Claude Code 也會先載入它的設定。現在主 Agent 與角色把它當成你自己的儲存庫來讀，並執行它的程式碼，除非你在這個 session 說不得執行；cc-feather 也不提供在你信任儲存庫之前檢查它的功能。代價是[儲存庫安全](#儲存庫安全)列出的風險都由你承擔。（[ADR 0016](docs/adr/0016-delegation-trusts-the-repository.md)）
- **新的 context，通常是同一個模型。**每次審查都在新的 context 中自行取得證據，但通常跟主 Agent 用同一個模型。成本與模型多樣性是你用 `/cc-feather:model` 選擇的角色設定，計畫要切成多細的 claim 則由規劃步驟決定。（[ADR 0003](docs/adr/0003-review-cost-and-independence-stay-user-configured.md)）

## 交接相容性

```text
/cc-feather:handoff 保存目前工作
/cc-feather:handoff 列出目前交接
/cc-feather:handoff 讀取登入功能交接
/cc-feather:handoff 接續登入功能
/cc-feather:handoff 搜尋提到登入的完成紀錄
/cc-feather:handoff-list
/cc-feather:handoff-history
/cc-feather:handoff-history login
/cc-feather:handoff-save login
/cc-feather:handoff-resume login
/cc-feather:handoff-tidy
/cc-feather:handoff-tidy login
```

沿用 [codex-feather](https://github.com/xenciscbc/codex-feather) 的 `.feather/handoffs/<work>.md`、`history.md` 與 `archive/<batch>.md`。讀取不接續執行；接續核對來源後繼續已授權工作。完成自動歸檔，失敗保留可重試資料；清除與封存需要明確範圍。來源基準只涵蓋選定檔案，不代表測試通過。明確指定 Claude memory 才做外部記憶唯讀查找。Handoff tidy 透過同一個交接工具與紀錄格式，寫入你確認的部分。

同一個 Git 儲存庫的各個 checkout 共用一個交接存放處：未追蹤交接紀錄的 linked worktree 會把紀錄存在 main worktree 的 `.feather/handoffs/`，所以移除或封存 worktree 不會再刪掉它們，而在任一個 checkout 中的 session 都列出同樣的工作、搜尋同一份歷史。來源、來源基準與紀錄的環境仍描述 session 所在的 checkout。追蹤自己紀錄的 checkout、非 Git 專案與明確指定的根目錄保留自己的存放處，跨專案也不做任何同步。linked worktree 中的 session 需要能寫入 main worktree 的存放處；作業系統或 session 的 sandbox 拒絕時，工具回報 `store-unwritable`，不會改寫在 worktree 中。完成、archive、clear、seal 與 adopt 會在存放處取得歷史鎖，所以共用它的 session 不會互相弄丟完成紀錄；寫入工作檔不取鎖，所以每項工作仍只有一個寫入者。較早版本留在其他 checkout 的紀錄會連同那個 checkout 列出，`adopt` 會把你確認的部分移到目前的存放處。在 codex-feather 採用同一個 runtime 之前，Codex session 仍把紀錄寫在 linked worktree 內，Claude session 的列表會把它們列為另一個 checkout 的存放處。交接工具依原有規則處理 Git 忽略與使用者追蹤選擇。

## Checkout lease

```text
/cc-feather:setup 在使用者範圍安裝 Checkout lease 規則
/cc-feather:worktrees
```

Checkout lease 是一份合作式紀錄，表示某個 session 正在使用 Git 儲存庫的某一個 checkout（main worktree 或 linked worktree）來修改它。它只聲明使用與開始時間，從不證明持有者仍在執行；取得 lease 也從不授權變更、重設或移除該 checkout 原有的內容。安裝 `leases` setup 元件後，主 Agent 在變更 checkout 之前取得 lease，在里程碑、受阻、停下來等你之前與完成時續期，不再使用該 checkout 時歸還；子 agent 從不取得 lease，而是在主 Agent 的 lease 下工作。lease 由其他 session 持有，或 worktree 上有其他 lock 時，主 Agent 會停下，列出持有者、目的、開始時間、最後回報的活動與經過時間，由你選擇：在 main worktree 工作、使用閒置的 worktree、開新的 worktree，或接手你判斷已被遺留的 lease。lease 從不自動接手，也沒有任何經過時間會讓 lease 算作被遺留。平行的 worktree 工作合併完成、不再使用時，主 Agent 會先停放（park）再歸還它的 lease：乾淨且 branch 已包含在預設 branch（或工作接續所在的 branch）中的 worktree 會 detach 它的 HEAD；停放從不刪除 branch 或 worktree。`/cc-feather:worktrees` 列出每個 checkout 的 lease、lock、未提交與未追蹤的變更、相對預設 branch 領先與落後的 commit，以及提到它的交接紀錄；它只回報事實，從不說某個 checkout 是空閒的。規則寫在 [leases skill](skills/leases/SKILL.md)。

`leases` 元件只有你指名選擇時才安裝，`both` 從不包含它。project 範圍的規則區塊位於該 checkout 的 CLAUDE.md，而在 linked worktree 中啟動的 session 只載入該 worktree 自己的 CLAUDE.md，所以只有區塊已被追蹤、已 commit，並且（對 Claude Code 以遠端預設 branch 為基礎建立的 worktree）已 push 時，那個 session 才看得到 lease 規則。要讓每個 session 都遵守，請在使用者範圍安裝 `leases`，或 commit 並 push project 的 CLAUDE.md 區塊。handoff 與 agent 分派元件的 project 範圍區塊也是如此。

lease 存在 main worktree 下的 `.feather/leases/`，每個 checkout 一個 `<key>.json`，以 Git 對每個 worktree 的管理識別為 key，main worktree 用 `.main`；這個目錄會忽略自己。linked worktree 上持有中的 lease 另由原因為 `cc-feather lease <lease_id>` 的 Git worktree lock 保護，所以 `git worktree prune`、一般的 `git worktree remove` 與 Claude Code 的清理都不會動到那個 worktree，不讀 lease 的工具也看得出它正在使用；Git 無法鎖定 main worktree。在 session 自己剛建立的 worktree 中，它觀察到的 Claude Code session lock 會取代 lease 自己的 lock 而被接受。這依賴 Claude Code 的清理會略過已鎖定的 worktree，而且從不解除不是它設定的 lock。互動式 Claude Code session 結束時會解除自己的 session lock，而 headless 的 `-p` 執行會留下它，所以互動式 session 結束時仍持有的 lease 會沒有 lock，直到下一次列出或取得時以 lease 自己的 lock 重新鎖定。其他工具要讀取的紀錄欄位見 [setup 文件](docs/setup.md#checkout-leases)。

lease 是合作式的：它只約束遵守規則的 session。它不會停止、偵測或管理其他 session 的 process，也不會把忽略 lease 的人或工具（包括 codex-feather 的 session）擋在 checkout 之外。Windows 與 WSL 之間、或不同機器之間共用同一個 checkout 不在涵蓋範圍內。

## 更新、移除與驗證

Plugin 更新只更新套件，需另跑 setup update 更新選定的已部署項目，完成後開新 session，因為角色與指引在 session 開始時載入。0.45.0 讓 `/cc-feather:test-speedup` 也檢查不屬於測試程式碼本身的設定與執行參數，尤其是與並行、隔離、記憶體和時間有關的部分，依實際生效的值判斷（包括框架的預設值），並把每個 Unbounded run configuration 列在第四節「有資源風險的執行設定」；它依序查詢已安裝版本的檔案、官方文件與 changelog、官方 issue tracker，查不到的就回報為未知。提高並行度的加速建議會說明它造成的 worker 數量與對記憶體的影響；量測會用不改任何檔案的命令列覆寫限制被標出的執行，或改在 Runner 內執行，詳見[設計與測試檢查](docs/reference.zh-TW.md#設計與測試檢查)。主機、作業系統或其他工具因記憶體或其他資源不足而停下的測試執行，現在回報為未完成，絕不算失敗，沒有你的同意不會再跑；這樣停下的 final check 算是沒有執行的 final check，詳見[資源限制](docs/reference.zh-TW.md#資源限制)。它改了 verifier、adversary、executor 與 security-executor 的角色定義，所以既有安裝要先更新 plugin，再於每個裝有分派元件的範圍執行 `/cc-feather:setup update`，然後開新 session；在那之前，check 會回報這些角色來自較舊的範本。要回到 0.44.0，重新安裝 0.44.0 的 plugin，並在每個裝有分派元件的範圍執行 `/cc-feather:setup update`，再開新 session；不需要先移除。0.44.0 讓 `/cc-feather:test-speedup` 也找出能以更小規模驗證同一事實的測試：只有在大小不是測試要驗證的對象時，才建議改用較小的輸入、資料集、迭代次數或 fixture；刪除也可以是替換，也就是報告中描述的一個較小測試，只有在較重的測試所驗證的其他每件事都有既有測試繼續驗證時才提出。 量測的提議也可以對最慢的測試做 profiling，同樣經你同意才執行，詳見[設計與測試檢查](docs/reference.zh-TW.md#設計與測試檢查)。 `git diff v0.42.1 HEAD -- templates scripts` 沒有任何差異，所以 0.44.0 沒有改任何已安裝的指引、政策範本、角色定義或設定工具，只改了 plugin 從套件載入的一個 skill；既有安裝需要更新 plugin 再開新 session，不需要做 `/cc-feather:setup update`。 要回到 0.43.0，重新安裝 0.43.0 的 plugin；不需要 setup update，也不需要先移除。 0.43.0 讓主 Agent 在計畫開始實作後每次停下來等你時，都在對話中以結束它回合的訊息提出，不用提問工具，列出你要決定的事與你的選項；你自己的訊息就是回答。 審查等級的提問與 READY 之後的提問在實作開始前提出，仍使用提問工具。 `git diff v0.42.1 HEAD -- templates scripts` 沒有任何差異，所以 0.43.0 沒有改任何已安裝的指引、政策範本、角色定義或設定工具，只改了 plugin 從套件載入的流程；既有安裝需要更新 plugin 再開新 session，不需要做 `/cc-feather:setup update`。 要回到 0.42.1，重新安裝 0.42.1 的 plugin；不需要 setup update，也不需要先移除。0.42.1 讓交接工具拒收控制字元：標題或欄位含有 U+0000–U+001F 或 U+007F，或 `details`、`replacement` 含有 TAB、LF、CR 以外的控制字元時，`create` 與 `update` 回傳 `input`，指出是哪個值、哪個字元與它的位置，且不寫入任何東西。 這類字元通常來自不小心的跳脫，例如以非 raw 的 Python 字串表示 Windows 路徑時的 `\a` 或 `\t`，工具以前會默默存下；已經含有這類字元的紀錄不檢查也不修改。 `git diff v0.42.0 HEAD -- templates scripts` 沒有任何差異，所以 0.42.1 沒有改任何已安裝的指引、政策範本、角色定義或設定工具，只改了 plugin 從套件載入的交接工具與它的參考文件；既有安裝需要更新 plugin 再開新 session，不需要做 `/cc-feather:setup update`。 要回到 0.42.0，重新安裝 0.42.0 的 plugin；不需要 setup update，也不需要先移除。0.42.0 新增審查等級（Review level）：在 auto 下，依計畫施工的計畫在第一個 claim 實作之前，主 Agent 會為這份計畫建議 `standard`、`light` 或 `off` 並附上一行理由，由你選擇，如[審查等級](#審查等級)所述。 `standard` 照舊執行自動流程，`off` 對這份計畫關閉自動審查，`light` 也關閉它，但會讓主 Agent 請 reviewer 審查每個 claim 的程式碼、執行每項驗收並回報結果，之後在對話中停下，列出剩下的工作，包括合併。 `git diff v0.41.0 HEAD -- templates scripts` 沒有任何差異，所以 0.42.0 沒有改任何已安裝的指引、政策範本、角色定義或設定工具，只改了 plugin 從套件載入的 skill 與流程；既有安裝需要更新 plugin 再開新 session，不需要做 `/cc-feather:setup update`。 要回到 0.41.0，重新安裝 0.41.0 的 plugin；不需要 setup update，也不需要先移除。 0.41.0 新增 `/cc-feather:handoff-history`，一個只能由你執行的唯讀指令，用來瀏覽已完成的交接歷史。 不帶參數時，它由新到舊列出最近 10 筆完成紀錄的編號標題；參數可依完成日期、日期區間、工作標題或關鍵字篩選，`sealed` 納入已封存的歷史，結尾的數字或 `all` 決定筆數，回覆編號即可看那幾筆的全文。 `/cc-feather:handoff-list` 與 `/cc-feather:handoff-resume` 在沒有待辦或未完成的工作時，現在會提示這個指令，但不會開啟歷史。 `git diff v0.40.0 HEAD -- templates skills/setup scripts` 沒有任何差異，所以 0.41.0 沒有改任何已安裝的指引、政策範本、角色定義或設定工具，只改了 plugin 從套件載入的 skill；既有安裝需要更新 plugin 再開新 session，不需要做 `/cc-feather:setup update`。 要回到 0.40.0，重新安裝 0.40.0 的 plugin；不需要 setup update，也不需要先移除。 0.40.0 新增 `/cc-feather:merge-upstream`，一個只能由你執行的指令，用於在 auto 下等待合併期間遠端預設 branch 移動了的計畫，如[合併上游](docs/reference.zh-TW.md#合併上游)所述。你同意後，主 Agent 在本機 fetch 遠端預設 branch 並把它 merge 進計畫的 branch，絕不 rebase、pull 或 force，這一步也不推送任何東西；這次 merge 的整合報告要經過計畫審查與你的核可，被它重新開啟的審查會再跑一次，之後這份計畫只在你親自下令或接受並合併時才合併。審查狀態規則現在在每個 session 都保有這些規則：merge commit 與它帶進來的 commit 絕不算在任何 claim 的判斷範圍內；自動合併不適用於有 Upstream merge 的計畫，也不會合併含有 merge commit 的範圍；在報告要求的每項通過都完成之前，主 Agent 不推送任何包含這次 merge 的 commit，除非你要求提早推送；自動合併因遠端預設 branch 移動而停下時，它的回報會建議這個指令。`git diff v0.39.0 HEAD -- templates skills/setup scripts` 沒有任何差異，所以 0.40.0 沒有改任何已安裝的指引、政策範本、角色定義或設定工具，只改了 plugin 從套件載入的 skill 與流程；既有安裝需要更新 plugin 再開新 session，不需要做 `/cc-feather:setup update`。要回到 0.39.0，重新安裝 0.39.0 的 plugin；不需要 setup update，也不需要先移除。0.39.0 沒有 Upstream merge 的規則，所以回到 0.39.0 之前，先合併 dispatch 紀錄中有 Upstream merge 的計畫。0.39.0 讓你對主 Agent 提問的回答，和你自己的訊息一樣，能提出或解除執行儲存庫程式碼的限制，並指定隔離環境，off 與 auto 下都是如此，如[儲存庫安全](#儲存庫安全)所述。解除限制或指定隔離環境需要明確指出它的話，包括你對指出它的主 Agent 提問回答「是」；回答其他問題的內容，以及沒有指出任何東西的「繼續」或「是」，不會解除限制，也不會指定環境；不清楚的話什麼也不解除、什麼也不指定，主 Agent 會再問；主 Agent 只從 context 壓縮摘要、紀錄或角色報告得知的回答，什麼也不解除、什麼也不指定。自動合併的說明現在也寫明（規則本來就是如此）你對主 Agent 提問的回答也能解除 session 的 `off`；READY 之後的最終檢查範圍提問也不再說成只問一次：之後的計畫審查建議不同或主 Agent 無法判斷是否不同時會再問，你要求更改範圍時主 Agent 也會再問。和 0.38.0 一樣，它沒有改任何已安裝的指引、政策範本或角色定義，只改了 plugin 從套件載入的流程，所以既有安裝需要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`。要回到 0.38.0，重新安裝 0.38.0 的 plugin；不需要 setup update，也不需要先移除。0.38.0 修改 auto 下的最終檢查範圍：主 Agent 在提出每個範圍問題之前，先在計畫的分派紀錄中把它標為待答，在你的回答（你自己的訊息，或你對主 Agent 提問的回答）記錄下來之前，範圍是 `full`；在 `full` 下，整體驗收自己的執行若明顯以相同條件執行過某個 claim 主要驗收的指令，就逐一代替該指令，不再重跑；release 或建立 tag 時執行 `full`，除非你為那個 commit 選擇 `related`，詳見[自動審查](docs/reference.zh-TW.md#自動審查)。`v0.37.0`（位於 6cbb1b5）帶有這一版修正的缺陷，它的對抗式審查判定它違反 0.37.0 規格的 S2（BROKEN）：擴大範圍的回答若在主 Agent 記錄之前被 context 壓縮遺失，可能留下較舊、較窄的範圍，所以使用 0.37.0 的話請更新。它沒有改任何已安裝的指引、政策範本或角色定義，只改了 plugin 從套件載入的流程，所以既有安裝只要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`。要回到 0.37.0，重新安裝 0.37.0 的 plugin，這會帶回這個缺陷；不需要 setup update，也不需要先移除。0.37.0 會在沒有任何變更時，跨 session 與 context 壓縮沿用計畫分派紀錄中記錄的最終檢查通過結果；讓你依計畫審查的建議，在 READY 之後的提問中為每個計畫選一次最終檢查範圍 `full` 或 `related`；並新增自動合併：一項選用設定，預設關閉，開啟時，在 auto 下計畫最後的決定裡沒有任何項目需要你決定接受並合併時，主 Agent 不再詢問，只以 fast-forward 推送最終檢查與審查判斷過的 commit 來合併計畫，絕不 release 或建立 tag；另新增設定它的 `/cc-feather:auto-land`，詳見[自動審查](docs/reference.zh-TW.md#自動審查)與[自動合併](#自動合併)。它為了計畫審查的最終檢查範圍建議改了 analyst 的角色定義，所以既有安裝要先更新 plugin，再於每個裝有分派元件的範圍執行 `/cc-feather:setup update`，然後開新 session；在那之前，check 會提醒 analyst 來自較舊的範本。0.36.x 或更舊的設定工具會以 `invalid delegation state schema` 拒絕已儲存自動合併設定的範圍且不做任何變更，所以要回到 0.36.0，先在每個儲存過它的範圍以 `/cc-feather:auto-land default project` 或 `/cc-feather:auto-land default user` 把它設回 `default`，再重新安裝 0.36.0 的 plugin，並在每個裝有分派元件的範圍執行 `/cc-feather:setup update`，再開新 session，讓它還原 0.36.0 的 analyst 角色定義；session 的選擇不需要任何處理，也不需要先移除。0.36.0 新增兩個只能由你執行的指令，都只出報告、不改任何檔案：`/cc-feather:test-speedup` 找出讓測試變快又不削弱驗證內容的方法，先做靜態分析，經你同意才量測；`/cc-feather:overdesign-check` 找出剛才討論的提案或你指定對象中的過度設計，詳見[設計與測試檢查](docs/reference.zh-TW.md#設計與測試檢查)。它沒有改任何已安裝的指引、政策範本、角色定義或 setup 程序，所以既有安裝只要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`。要回到 0.35.0，重新安裝 0.35.0 的 plugin；不需要 setup update，也不需要先移除。0.35.0 讓計畫審查的資源風險標示成為由你採用或捨棄的提議：計畫的計畫審查回傳 READY 之後、它的第一個 claim 實作之前，主 Agent 只問你一次要採用哪些提議的標示，列出每項的理由與估計並附上自己的建議，採用的 claim 需要的預算問題也併入同一個問題，所以一連串的 claim 之後不會再為了標示或預算停下，詳見[參考文件](docs/reference.zh-TW.md#資源限制)。只有你採用的 claim 才是 Resource-risk claim；你捨棄的 claim 是一般的 claim，仍受 Unbounded probe 底線涵蓋，沒有任何提議標示的計畫不會多出新的問題。它改了 analyst 的角色定義，所以既有安裝要先更新 plugin，再於每個裝有分派元件的範圍執行 `/cc-feather:setup update`，然後開新 session；在那之前，check 會提醒 analyst 來自較舊的範本。要回到 0.34.0，重新安裝 0.34.0 的 plugin，並在每個裝有分派元件的範圍執行 `/cc-feather:setup update`，再開新 session，讓它還原 0.34.0 的 analyst 角色定義；不需要先移除。0.34.0 新增相關測試驗收：一項 agent 分派設定，開啟時主 Agent 在 Claim 的驗收中列出與變更相關的測試模組，而不是完整測試，計畫的整體驗收仍是完整測試，由最終檢查執行；另新增設定它的 `/cc-feather:related-tests`，詳見[相關測試驗收](#相關測試驗收)。它沒有改任何角色定義或 handoff、分派與 leases 的政策範本，所以既有安裝只要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`，而且某個範圍在儲存這項設定之前，指引與狀態都保持逐位元組相同。0.33.x 或更舊的設定工具會以 `invalid delegation state schema` 拒絕已儲存這項設定的範圍且不做任何變更，所以要回到 0.33.0，先在每個儲存過它的範圍以 `/cc-feather:related-tests default project` 或 `/cc-feather:related-tests default user` 把它設回 `default`，再重新安裝 0.33.0 的 plugin；session 的選擇不需要任何處理。0.33.0 新增 Checkout lease：存在 main worktree 下 `.feather/leases/` 的合作式紀錄，表示某個 session 正在使用 Git 儲存庫的某一個 checkout 來修改它，在 linked worktree 上另由 Git worktree lock 保護；選用的 `leases` setup 元件告訴主 Agent 何時取得、續期與歸還 lease；`/cc-feather:worktrees` 列出每個 checkout 的 lease、lock 與留在其中的工作，詳見 [Checkout lease](#checkout-lease)。lease 只約束遵守規則的 session，它的 lock 依賴 Claude Code 的清理會略過已鎖定的 worktree。它沒有改任何角色定義或 handoff 與分派的政策範本，setup 工具只新增 `leases` 元件，而 `both` 從不包含它，所以既有安裝只要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`。要使用 lease，請安裝 `leases` 元件；project 範圍的區塊只透過 linked worktree 自己的 CLAUDE.md 才能到達在那裡啟動的 session，所以要讓每個 session 都遵守規則，請在使用者範圍安裝，或 commit 並 push project 的 CLAUDE.md 區塊，handoff 與分派元件也是如此。要回到 0.32.0，先在每個裝有 `leases` 元件的範圍執行 `/cc-feather:setup remove` 移除它，因為 0.32.0 的 setup 工具會以 `state component schema mismatch` 拒絕這樣的範圍且不做任何變更，再重新安裝 0.32.0 的 plugin。重新安裝之前請歸還仍持有的 lease，因為 0.32.0 沒有 lease 工具，被遺留的 lease 會保留它的 Git worktree lock，直到 `git worktree unlock` 移除它。0.32.0 新增資源風險執行：計畫審查把執行檢查或驗證時可預見會耗盡記憶體、時間或機器的 claim 標為 Resource-risk claim，並為有風險的部分提出 Execution method，主 Agent 以來自你、計畫或你的指引的預算核准它，角色只在 Runner 內執行那個部分（Runner 是分派 skill 中新增的啟動器，限制一個指令整個 process tree 的記憶體、它的時間與輸出），界限不明或不符合預算的新的或修改過的測試或 probe 交回主 Agent 而不執行，交回或被停下的部分記為 Observed resource risk，詳見[參考文件](docs/reference.zh-TW.md#資源限制)。cc-feather 不規定任何預算，硬性限制只涵蓋透過 Runner 執行的指令，不涵蓋交給已經在執行的服務的工作，也不涵蓋在 shell 之外執行程式碼的工具。Runner 的呼叫經過你平常的權限處理；不要新增允許所有 Runner 呼叫的權限規則，因為這種規則等於允許任何指令透過 Runner 執行。它改了 analyst、executor、security-executor、verifier、reviewer 與 adversary 的角色定義，所以既有安裝要先更新 plugin，再於每個裝有分派元件的範圍執行 `/cc-feather:setup update`，然後開新 session；在那之前，check 會提醒這些角色來自較舊的範本。要回到 0.31.0，重新安裝 0.31.0 的 plugin，並在每個裝有分派元件的範圍執行 `/cc-feather:setup update`，再開新 session，讓它還原 0.31.0 的角色定義；不需要先移除。0.31.0 把 linked worktree 的交接紀錄存在 main worktree 的存放處，新增歷史鎖與清除過期鎖的 `unlock` 指令，列出留在其他 checkout 的紀錄，並以 `adopt` 移動你確認的部分，詳見[交接相容性](#交接相容性)。這一版同樣沒有改任何角色定義、已安裝的政策範本或 setup 工具對它們的產生方式，所以既有安裝只要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`。在 codex-feather 採用同一個 runtime 之前，Codex session 仍把紀錄寫在 linked worktree 內；Claude session 的列表會把它們列在那個 checkout 的存放處下，`adopt` 會移動你確認的部分。要回到 0.30.0，重新安裝 0.30.0 的 plugin 即可；不需要做 setup update 或先移除，寫入 main worktree 存放處的紀錄在 main worktree 中仍可由 0.30.0 讀取，而 linked worktree 中的 0.30.0 session 又只會看到該 worktree 自己的紀錄。0.30.0 把每條分派規則只寫在負責它的檔案中，其他適用的地方改為指向它，主 Agent 在依賴 review state 的決定之前會完整讀過它；[參考文件](docs/reference.zh-TW.md)改為說明每條規則的用途並連到寫明它的流程，沒有任何規則改變。以連結所及的所有檔案計算，每個入口少載入約 9 KB；以主 Agent 被指示讀取的檔案計算，每個入口都載入更多，其中預覽、Stop threshold 指令與 claim 實作的 brief 增加最多，因為它們現在要完整讀 review state；兩種計算都記錄在[結果檔](docs/specs/delegation-dedupe-results.md#loading-cost)。它沒有改任何角色定義、已安裝的政策範本或 setup 工具對它們的產生方式，所以既有安裝只要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`。要回到 0.29.0，重新安裝 0.29.0 的 plugin 即可；不需要做 setup update 或先移除。0.29.0 讓分派信任儲存庫：主 Agent 與角色用一般的檔案工具與一般的 Git 指令讀取它，審查只保留讓結果正確的檢查（`HEAD` 是該次呼叫判斷的 commit，claim 依賴的內容在呼叫前後都沒有未提交或未追蹤的變動，commit 只包含 claim 的檔案），而且除非你在這個 session 中限制，審查會執行儲存庫的程式碼；要不要信任一個儲存庫由你決定，剩下的風險列在[儲存庫安全](#儲存庫安全)。說明變更來自別人已經不會阻止審查執行它，所以要阻止，請在你自己的訊息中說程式碼不得執行。它改了 reviewer、verifier、adversary、analyst、scout 與 Explore 的角色定義以及已安裝的分派政策，所以既有安裝要先更新 plugin，再於每個裝有分派元件的範圍執行 `/cc-feather:setup update`，然後開新 session；在那之前，check 會提醒這些角色（以及 `auto` 下的分派指引）來自較舊的範本。要回到 0.28.0，重新安裝 0.28.0 的 plugin，並在每個裝有分派元件的範圍執行 `/cc-feather:setup update`，再開新 session，讓它還原 0.28.0 的角色定義與政策；不需要先移除。0.28.0 要求主 Agent 依問題提出或採用一項要求或修正之前，先簡短說明這個情況在一般使用中或適用的威脅模型下何時會發生、最壞而可信的後果，以及既有規則是否已經涵蓋，並優先沿用或修正既有規則；這項權衡不改變什麼會擋下。它改了已安裝的分派政策，讓主 Agent 在提出或採用這類要求或修正之前也會載入分派 skill，所以既有安裝要先更新 plugin，再於每個裝有分派元件的範圍執行 `/cc-feather:setup update`，然後開新 session；在那之前，check 會提醒分派指引來自較舊的範本。要回到 0.27.1，重新安裝 0.27.1 的 plugin，並在每個裝有分派元件的範圍執行 `/cc-feather:setup update`，再開新 session，讓它還原 0.27.1 的政策；不需要先移除。0.27.1 修正 `/cc-feather:handoff-tidy` 的兩條寫入規則：一次確認要寫入同一份紀錄多次時（例如兩項合併進同一個目標），現在能全部寫完，每次寫入都以前一次寫入存下的內容為基礎，不會蓋掉前一次加入的內容；這個指令完成的紀錄若封存失敗，會依交接 skill 的規則重試。它只改了這個指令的文字，沒有改任何已安裝的角色定義或政策，所以既有安裝只要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`。要回到 0.27.0，重新安裝 0.27.0 的 plugin 即可；不需要做 setup update 或先移除。0.27.0 新增 `/cc-feather:handoff-tidy`：只能由你執行的指令，從交接紀錄建議下一項工作，指出可合併、過時或不完整的紀錄，或不執行專案程式碼，拿指定或全部工作的紀錄項目對照目前專案，並只寫入你確認的部分。它沒有改任何已安裝的角色定義或政策，所以既有安裝只要更新 plugin 再開新 session；不需要做 `/cc-feather:setup update`。要回到 0.26.0，重新安裝 0.26.0 的 plugin 即可；不需要做 setup update 或先移除，這個指令寫入的紀錄仍是一般的交接紀錄。0.26.0 改了 `auto` 下計畫的審查方式：每個 claim 完成時就審查並保留它的通過結果，最終檢查會重跑每個 claim 的主要驗收，並以修正用的 claim 修正失敗，對抗式審查只在最終 commit 執行一次並記錄它的發現，派工紀錄讓審查狀態跨 session 延續，主 Agent 只在最後問你一次。它只改了分派 skill 的流程，沒有改任何已安裝的角色定義或政策，所以既有安裝只要更新 plugin 再開新 session，新 session 就會使用新的流程；不需要做 `/cc-feather:setup update`。要回到 0.25.0，重新安裝 0.25.0 的 plugin 即可；不需要做 setup update 或先移除，較早的版本會忽略留在 `.feather/dispatch/` 下的派工紀錄。從 0.25.0 起，審查不再詢問就會執行儲存庫的程式碼，而審查別人的變更時，需要由你說明它來自別人。詳見[儲存庫安全](#儲存庫安全)。此外，較早版本的安裝在更新前仍保留舊的指引格式，check 也會提醒分派指引來自較舊的範本。移除 plugin 不會自動刪除外部角色／政策，請先移除想清理的 setup scope。使用者修改過的管理檔會保留為衝突，交接紀錄不刪除。

```text
/cc-feather:setup 更新目前專案已安裝的角色與指引，保留模型與審查模式
/cc-feather:setup 移除目前專案由 cc-feather 管理的角色與指引
```

若先前安裝在 user 範圍，請明確指定更新／移除使用者範圍。移除角色與指引後，再透過 Claude 的 plugin 管理介面解除安裝套件。

[交接相容性驗證](docs/compatibility.md)記錄原有測試；新增 setup/model 的測試與限制見[設定驗證](docs/setup-validation.md)。設定與政策檔案檢查不等於已驗證真實 Claude 派工。計畫審查輪數與派工條件是模型指引，沒有 hook 強制計數；本套件不以設定成功宣稱 live model 已確認。

## Agent 名稱與舊版升級

原生名稱直接使用 `scout`、`analyst`、`mech-executor`、`executor`、`security-executor`、`verifier`、`reviewer`、`adversary`、`Explore`，不再有 `feather-` 前綴。

若已有其他 agent 使用同樣的名稱（即使位於不同檔名或子目錄），setup 會把 Explore 以外的角色都加上 `cc-` 前綴安裝（例如 `cc-scout`），並在分派規則中列出實際名稱；之後一直沿用前綴。其他 agent 的檔案不會被覆蓋或接管。Explore 維持原名；已有自己的 Explore 時直接沿用你的。`cc-` 名稱本身也衝突時，仍會保留檔案並請使用者決定。跨 user/project 範圍的同名角色依 Claude 優先序生效，需一併核對適用範圍。

舊版已管理的 `feather-*` 角色請執行 `/cc-feather:setup 更新目前專案的角色與指引`（user 安裝請指定使用者範圍）。Update 會預覽更名、保留 model／effort 及審查模式，只有完整且未被修改的舊角色才遷移；新名稱已被占用就停止。完成後開新 session。Model、永久審查開關與 session 匯出需先完成遷移；也可直接移除完整的舊版管理安裝。

## 致謝

代理角色與協作方式參考了 Nanako0129 的 [pilotfish](https://github.com/Nanako0129/pilotfish)。
