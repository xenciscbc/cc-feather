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
| `/cc-feather:adversarial-review <攻擊範圍> [路徑或 commit 範圍] [可拋棄目標]` | 執行你要求的對抗式審查，兩種模式都可用；見[安全關鍵工作](#安全關鍵工作) |
| `/cc-feather:model` | 查看、設定角色 model／effort，區分單次、session 與永久選擇 |
| `/cc-feather:auto-on` | 開啟依計畫施工的自動計畫審查、程式碼審查、結果驗證，以及安全關鍵 claim 的對抗式審查；主 Agent 之後可不經詢問，在通過前 commit 這類工作、推送到它為此工作建立的 branch 並開 pull request，但合併到預設 branch、release、回報完成與 ticket 完成仍需兩項通過（安全關鍵 claim 還要加上 HELD）或你的接受並合併決定 |
| `/cc-feather:auto-off` | 關閉自動審查 |
| `/cc-feather:stop-threshold <2–10 或 default> [範圍]` | 設定自動審查的[停止門檻](#停止門檻)：只用於這個 session（不帶範圍或 `session`），或儲存在 `project` 或 `user` 範圍 |

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
| agent 分派（delegation） | 獨立分派規則＋九個原生 agent；自動計畫審查預設關閉 | 移除完整的受管理角色及分派規則，保留 handoff 規則 |
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
| 安全關鍵實作 | security-executor | opus | high |
| 實作後驗證 | verifier | opus | high |
| 實作後程式碼審查 | reviewer | opus | high |
| 對抗式審查 | adversary | opus | high |

| 角色 | 何時使用 | 產出與權限 |
| --- | --- | --- |
| scout | 範圍明確的事實查找，例如定位定義、設定或引用 | 唯讀；回報檔案位置與證據，不做複雜因果分析。審查或安全分析時只讀取與搜尋主 Agent 列出的檔案與目錄，沒有清單時回報缺少需求而不讀取。 |
| Explore | 尚不清楚程式結構，需要較廣的模組、入口、呼叫關係探索 | 唯讀；建立理解程式的地圖，深入診斷交給 analyst。審查或安全分析時只讀取與搜尋主 Agent 列出的檔案與目錄，沒有清單時回報缺少需求而不讀取。 |
| analyst | 根因／影響分析、安全問題查找、實作前計畫審查 | 唯讀；回報證據、推論與建議；計畫審查回覆 READY／REVISE。審查或安全分析時只讀取與搜尋主 Agent 列出的檔案與目錄，沒有清單時回報缺少需求而不讀取。 |
| mech-executor | 規則、範圍與結果已明確的重複修改 | 可修改指定檔案；按完整規格執行，例如批次改名 |
| executor | 需要局部設計與工程判斷的功能或修正 | 可修改指定檔案並驗證，遇到架構或需求缺口交回主 Agent |
| security-executor | 影響授權、秘密資料、密碼學或信任邊界的實作 | 可修改指定檔案；驗證正常行為及濫用／拒絕案例 |
| verifier | 獨立確認完成的實作是否符合明確的 claim | 執行檢查與反例，不修改檔案；回覆 CONFIRMED／REFUTED／INCONCLUSIVE。它只依[儲存庫安全](#儲存庫安全)讀取儲存庫與執行其程式碼。 |
| reviewer | 獨立審查實作某個 claim 的程式碼 | 自行比對 base revision 與受審 commit，並讀取主 Agent 列出的未提交檔案，只跑 brief 指定的 lint 與型別檢查，不修改檔案也不跑測試；回覆 APPROVED／CHANGES_REQUESTED／INCONCLUSIVE。它只依[儲存庫安全](#儲存庫安全)讀取儲存庫與執行其程式碼。 |
| adversary | 嘗試攻破一個安全關鍵 claim，只針對 brief 指定的可拋棄目標 | 只有 Read、Glob、Grep、Bash，絕不修復程式碼；回覆 HELD／BROKEN／INCONCLUSIVE。只有 brief 把某個專案檔列為 fixture 並附上重設方式時才會改動它，且絕不在受把關的呼叫中改動。這些安全限制（這條 fixture 規則、只用 brief 指定、使用合成資料的可拋棄目標，不連外部主機）是給模型的指示，不是沙箱：Bash 仍可連網與寫檔，主 Agent 會在每次呼叫前後比對工作區。它只依[儲存庫安全](#儲存庫安全)讀取儲存庫與執行其程式碼。 |

主 Agent 保留需求理解、決策、整合與最後驗收。小型或脈絡高度耦合的工作直接處理；獨立子任務才分派，明確指定範圍、檔案 ownership 與完成條件。子 Agent 都是 leaf，不再往下分派，也不維護交接或進度紀錄，改由主 Agent 依其回報記錄。

每個欄位獨立套用優先序：**該次任務明確指定 > 適用的 session 指定 > 已儲存角色設定 > 套件預設**。例如「用 Sonnet 審查計畫」仍使用 analyst 職責，model 改為 Sonnet，未指定 effort 則保留 analyst 的 high。指定值無法原生套用時先說明，不暗中替換或只在 prompt 假裝設定成功。

安全分析由唯讀 analyst 做；安全關鍵變更（Security-critical change）的實作交給 security-executor。

自動審查預設關閉，用[開關](#自動審查開關)開啟或關閉。開啟後只涵蓋**依計畫施工的工作**：依你同意的計畫、spec、ticket 或對話中的計畫進行的工作。

| 步驟 | 時機 | 角色 | 通過條件 |
| --- | --- | --- | --- |
| 計畫審查 | 施工前 | analyst | READY |
| 程式碼審查 | 主 Agent 的主要驗收通過後，或依[儲存庫安全](#儲存庫安全)記為未執行時 | reviewer，自行取得 diff | APPROVED |
| 結果驗證 | APPROVED 之後 | verifier | CONFIRMED |
| 對抗式審查 | 安全關鍵 claim：在 auto 下，最終檢查在最後的 commit 上通過後，最後做一次；在 `off` 下，在同一個 commit 拿到 APPROVED 與 CONFIRMED 之後 | adversary | HELD |

重點如下；每條規則的完整說明見[參考文件](docs/reference.zh-TW.md#自動審查)：

- **沒有計畫的工作**不自動審查；但做出安全關鍵變更、資料遷移或不可逆操作之前，要先有一份經過審查、由你核准的書面計畫。
- **計畫就是你指名的東西。**要求主 Agent 實作時指名計畫、spec 或 ticket，就代表你同意它，而你指名的內容決定它的 claim：spec 是一個 claim，除非它自己列了 claim；一份 spec 的 ticket 是一個計畫，每張未完成的 ticket 一個 claim；單一 ticket 本身就是計畫和 claim。claim 的實作者與審查者讀的是 claim 本身和它引用的 spec 段落，不是整份 spec。
- **依 claim 審查的時機：**在 auto 下，每個 claim 一實作完並 commit，就做程式碼審查、再做結果驗證；依賴另一個 claim 的 claim，要等那個 claim 拿到有效的 APPROVED 與 CONFIRMED 才開始。之後計畫中另一個 claim 改到這個 claim 的檔案時，只要改動落在那個 claim 自己通過的審查所判斷的範圍內，這些通過結果就維持不變。
- **擋住 claim 的只有：**驗收沒有照所寫的達成、有 failing test 或重現步驟證明既有行為壞了、引入安全問題或資料遺失，或偏離計畫。其他問題都記進這份工作的後續紀錄，由你決定之後要不要開計畫修。
- **次數上限：**每個步驟連續沒通過的自動呼叫達到[停止門檻](#停止門檻)（預設 2）就停下來等你。次數只屬於同一個 session；在 auto 下，通過結果、對抗式審查結果與你的決定會透過 `.feather/dispatch/` 下這份計畫的派工紀錄跨 session 延續，主 Agent 照紀錄所寫的內容採信。
- **最終檢查與合併：**在 auto 下，主 Agent 可以在通過前 commit claim、推送到它為這份工作建立的 branch 並開 pull request。合併前，主 Agent 會在要合併的 commit 上跑計畫的整體驗收，並重跑每個 claim 的主要驗收；失敗時由造成失敗的 claim 或一個修正用的 claim 修正。在 auto 下，主 Agent 接著只在計畫結束時問你一次，列出每個 claim 的通過結果、缺少的部分，以及這套流程沒有檢查的事。合併到預設 branch、release、回報完成與 ticket 完成，都要等兩項通過（安全關鍵 claim 還要 HELD）或你的接受並合併決定。
- **明確要求**任何審查，兩種模式都可用，只跑你要求的部分，不占自動次數。
- **成本：**在預設停止門檻下，一次不中斷的過程中，每個 claim 最多 6 次自動呼叫，安全關鍵 claim 最多 8 次；每次重新打開的 claim、最終檢查的修正或核准的偏離都會再增加呼叫；其他門檻的公式與降低成本的方法見參考文件。

完整規則見[計畫審查](skills/delegation/references/plan-review.md)、[程式碼審查](skills/delegation/references/code-review.md)、[結果驗證](skills/delegation/references/outcome-verification.md)與[對抗式審查](skills/delegation/references/adversarial-review.md)程序；用語定義見 [CONTEXT.md](CONTEXT.md)。

### 安全關鍵工作

```text
/cc-feather:adversarial-review 檢查 src/auth 的 session token 驗證，使用計畫指定的測試伺服器
/cc-feather:adversarial-review 密碼重設流程 HEAD~3..HEAD
```

安全關鍵 claim 會改變信任邊界上的安全保證或某個安全控制，例如驗證、授權、session、憑證、密碼學或輸入驗證；主 Agent 依它做了什麼來判斷，而不是看關鍵字。它由 security-executor 實作，`off` 下也一樣。在 `auto` 下，它的計畫先做一次唯讀的安全分析，分析結果寫成 claim 驗收中的安全不變式，接著才做計畫審查。adversary 會對可拋棄的目標嘗試攻破這個 claim，回覆 HELD、BROKEN 或 INCONCLUSIVE。在 `auto` 下，它只在最終檢查於最終 commit 通過後，在那個 commit 執行一次；BROKEN 會被記錄下來，列在計畫結束時給你決定，而不是在計畫中修正。在 `off` 下，它在同一個 commit 拿到有效的 APPROVED 與 CONFIRMED 之後執行，BROKEN 要回去修。變更之前就存在的漏洞會成為你 tracker 裡的另一項工作，攻擊細節不寫進公開紀錄。`/cc-feather:adversarial-review` 隨時可以照你的要求執行對抗式審查，兩種模式都可用。adversary 的限制是給模型的指示：只有你的權限設定、hooks、Claude Code sandbox 或隔離環境能強制執行。詳見參考文件的[安全關鍵工作](docs/reference.zh-TW.md#安全關鍵工作)。

### 儲存庫安全

**審查別人的變更時，例如別人的 pull request、branch 或 patch，請在你自己的訊息中說明它來自別人：審查預設會執行你的儲存庫的程式碼，而你沒有說明來源的變更，會像你自己的變更一樣被執行。**

審查把受審儲存庫當成攻擊者可控制的內容來讀：Git 指令以固定形式執行，不執行儲存庫選定的任何程式；檔案要先通過連結與位置檢查才會讀取；主 Agent 在每次呼叫前後比對工作區。審查預設會在這台機器上執行儲存庫的程式碼，例如測試、build、linter 與探測；只有你在自己的訊息中說明某個變更來自別人，或說不可執行程式碼時才會停止，之後只在你指定的隔離環境中執行。`git add`、commit、tag 與 push 會使用你自己的 Git 設定所指定的程式，包含 hooks。這些規則是給模型的指示，不是 sandbox；[參考文件](docs/reference.zh-TW.md#儲存庫安全)列出全部規則與剩餘風險。詳見 [ADR 0011](docs/adr/0011-reviews-treat-the-repository-as-hostile-by-instruction.md) 與 [ADR 0014](docs/adr/0014-reviews-execute-repository-code-by-default.md)。

### 自動審查開關

```text
/cc-feather:auto-on
/cc-feather:auto-off
/cc-feather:auto-on project
/cc-feather:auto-off user
```

不帶參數（或加 `session`）只影響目前 session；加 `project` 或 `user` 則永久儲存至該範圍既有的 setup 安裝。保留 Claude plugin 的 `cc-feather:` 命名空間，指令名稱不再重複 `feather-`。

預設 `off` 不自動觸發；開啟後的 `auto` 審查依計畫施工的工作，並讓主 Agent 不經詢問，在 claim 通過前先 commit、推到它為這項工作建立的 branch，以及開 PR 列出尚未驗收的 claim；進入預設 branch、release、回報完成與把 ticket 設成完成，仍要等兩關都通過（安全關鍵 claim 還要加上 HELD），或你明確決定「接受並合併」（見[參考文件](docs/reference.zh-TW.md#自動審查)的 Commit 條件與你的決定）；兩者都接受明確要求的審查。永久設定不會取消另行指定的單次／session 偏好。可用 setup 查詢已儲存模式；更新保留永久選擇，切換不會讓既有計畫或 claim 的各步驟次數歸零。

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

- **規則是指示，不是強制。**審查流程、儲存庫安全與角色限制都是給模型的指示。測試讓出貨的文字保持一致，但沒有任何 hook 或工具強制執行；真正的限制只來自你的權限設定、hooks、sandbox 或隔離環境。（[ADR 0011](docs/adr/0011-reviews-treat-the-repository-as-hostile-by-instruction.md)）
- **審查只讀窄範圍的內容。**每次審查只判斷一個 claim，只讀 claim 本身和它引用的 spec 段落，所以不會拿 claim 沒採用的段落來判斷，也不會被無關的問題淹沒。代價是後面 claim 的審查者可能不知道前面 claim 的設計意圖；跨 ticket 的設計意圖應該寫進 spec，由計畫審查檢查每張 ticket 都引用了適用於它的部分。（[ADR 0012](docs/adr/0012-claims-are-decided-by-what-the-user-names.md)）
- **每個 claim 完成時就審查，並保留它的通過結果。**前面 claim 的問題會在後面的 claim 疊上去之前被發現，後面 claim 經過審查的改動碰到共用檔案時，也不會讓前面每個 claim 都重審。代價是前面 claim 的某個性質，如果沒有任何會重跑的驗收檢查涵蓋，就可能被改壞而最終檢查沒發現。（[ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#fixed-passes)）
- **最終檢查重跑主要驗收，不是每一項。**主 Agent 在要合併的 commit 上重跑計畫的整體檢查與每個 claim 的主要驗收，失敗只修一次，由造成失敗的 claim 或一個修正用的 claim 修，而不是重開每個 claim。其他驗收項目，以及無法重跑的檢查（例如人工檢查），不會在那裡重做。（[ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#the-final-check-and-fix-claims)）
- **只有安全關鍵 claim 有攻擊步驟，而且只在最後做一次。**程式碼審查讀 diff，結果驗證確認 claim 成立，兩者都不會嘗試繞過它；所以只有安全關鍵 claim 會在計畫審查前做安全分析，並做對抗式審查。在 auto 下，對抗式審查只在最終 commit 做一次，而不是每次修正後都做。代價是它攻擊的 commit 沒有被該 claim 自己的程式碼審查與結果驗證整體判斷過，BROKEN 會記錄下來交給你決定，而不是在計畫中修正，安全關鍵的修正用 claim 也不做對抗式審查。（[ADR 0009](docs/adr/0009-security-critical-claims-get-an-adversarial-review.md)、[ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#adversarial-review-at-the-final-commit)）
- **只有驗收需要的東西擋住完成，安全除外。**驗收範圍外的正確性問題，或只是推測的 regression，會記下來留給之後的計畫，而不是一輪接一輪地修；變更引入的安全問題或資料遺失仍然會擋。（[ADR 0013](docs/adr/0013-only-what-a-claims-acceptance-needs-holds-its-completion.md)）
- **有上限的次數，而不是重試到通過為止。**每個步驟到停止門檻就停下等你，所以主 Agent 和審查者意見不合時，會交給你決定，而不是繼續消耗呼叫。（[ADR 0004](docs/adr/0004-consecutive-failure-review-budget.md)、[ADR 0010](docs/adr/0010-the-stop-threshold-is-one-configurable-number.md)）
- **次數只屬於自己的 session；審查狀態透過照寫採信的紀錄跨 session。**接續的 session 重新計數，並重跑最終檢查。在 auto 下，通過結果、對抗式審查結果與你的決定透過計畫的派工紀錄延續，主 Agent 照紀錄所寫的內容採信，所以改動紀錄就會改變主 Agent 的認知；在 `off` 下，先前 session 通過的 claim 在合併前會再審一次。（[ADR 0002](docs/adr/0002-session-scoped-review-counts.md)、[ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#the-dispatch-record)）
- **早點 commit，合併時只決定一次。**主 Agent 可以在通過前 commit 並開 pull request，讓環境被回收時不會遺失工作，每次審查也都判斷固定的 commit；合併、release 與完成仍要等通過或你的接受並合併決定，而在 auto 下這個決定只在計畫結束時做一次。（[ADR 0007](docs/adr/0007-commit-before-acceptance.md)、[ADR 0008](docs/adr/0008-repository-authority-acceptance-and-gate-lifetime.md)、[ADR 0015](docs/adr/0015-each-claim-is-reviewed-when-done-and-keeps-its-passes.md#the-decision-at-the-end)）
- **審查預設執行儲存庫程式碼，讀取時則當它不可信。**每個 session 都問一次是否信任儲存庫，會卡住從交接接續的工作，所以審查現在預設會執行程式碼，除非你說明某個變更來自別人；沒有說明來源的變更會像你自己的一樣被執行。（[ADR 0014](docs/adr/0014-reviews-execute-repository-code-by-default.md)）
- **新的 context，通常是同一個模型。**每次審查都在新的 context 中自行取得證據，但通常跟主 Agent 用同一個模型。成本與模型多樣性是你用 `/cc-feather:model` 選擇的角色設定，計畫要切成多細的 claim 則由規劃步驟決定。（[ADR 0003](docs/adr/0003-review-cost-and-independence-stay-user-configured.md)）

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

Plugin 更新只更新套件，需另跑 setup update 更新選定的已部署項目，完成後開新 session，因為角色與指引在 session 開始時載入。0.26.0 改了 `auto` 下計畫的審查方式：每個 claim 完成時就審查並保留它的通過結果，最終檢查會重跑每個 claim 的主要驗收，並以修正用的 claim 修正失敗，對抗式審查只在最終 commit 執行一次並記錄它的發現，派工紀錄讓審查狀態跨 session 延續，主 Agent 只在最後問你一次。它只改了分派 skill 的流程，沒有改任何已安裝的角色定義或政策，所以既有安裝只要更新 plugin 再開新 session，新 session 就會使用新的流程；不需要做 `/cc-feather:setup update`。要回到 0.25.0，重新安裝 0.25.0 的 plugin 即可；不需要做 setup update 或先移除，較早的版本會忽略留在 `.feather/dispatch/` 下的派工紀錄。從 0.25.0 起，審查不再詢問就會執行儲存庫的程式碼，而審查別人的變更時，需要由你說明它來自別人。詳見[儲存庫安全](#儲存庫安全)。此外，較早版本的安裝在更新前仍保留舊的指引格式，check 也會提醒分派指引來自較舊的範本。移除 plugin 不會自動刪除外部角色／政策，請先移除想清理的 setup scope。使用者修改過的管理檔會保留為衝突，交接紀錄不刪除。

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
