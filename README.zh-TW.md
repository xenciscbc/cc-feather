# cc-feather

[English](README.md) | **繁體中文**

Claude Code plugin：相容 codex-feather 的交接紀錄，並提供角色分派、setup 與 model 設定。需要 Python 3.11+，僅使用標準函式庫。

## 安裝

將此版本推送至 [GitHub](https://github.com/xenciscbc/cc-feather) 後，在 Claude Code 執行：

```text
/plugin marketplace add xenciscbc/cc-feather
/plugin install cc-feather@cc-feather
```

本機 checkout 可用 `/plugin marketplace add D:/work_data/project/skill/cc-feather` 加入，再用相同 install 指令。開發時可用 `claude --plugin-dir /absolute/path/to/cc-feather`。安裝後開新 session；plugin 載入方式見 [Claude 官方文件](https://code.claude.com/docs/en/plugins)。

## 五個入口

| Skill | 用途 |
| --- | --- |
| `/cc-feather:handoff` | 保存、列出、讀取、接續工作，查詢／清除／封存完成歷史與來源基準 |
| `/cc-feather:setup` | 先查狀態，分別或一起管理 handoff 自動維護規則、agent 分派規則與角色安裝 |
| `/cc-feather:model` | 查看、設定角色 model／effort，區分單次、session 與永久選擇 |
| `/cc-feather:auto-on` | 開啟依風險觸發的自動計畫審查 |
| `/cc-feather:auto-off` | 關閉自動計畫審查 |

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
| handoff | `CLAUDE.md` 中獨立的自動維護規則 | 只移除提醒；交接紀錄與 plugin 的 handoff 指令仍保留 |
| agent 分派（delegation） | 獨立分派規則＋六個原生 agent；自動計畫審查預設關閉 | 移除完整的受管理角色及分派規則，保留 handoff 規則 |
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

兩項使用不同的 `CLAUDE.md` 管理區塊，安裝狀態在各範圍的 `cc-feather/state.json` 分項保存。handoff 規則不會自行建立新紀錄：仍需使用者要求建立或接續後，才在里程碑、受阻與完成時維護同一份紀錄。只查看／列出不啟用維護。

舊版將兩種規則放在同一區塊；升級會檢查擁有權並拆分，保留模型與審查設定。只移除分派不能順便刪掉原有 handoff 提醒；既有檔案被修改或名稱衝突時，先保留並交由使用者決定。

## 日常使用流程

1. 在要工作的專案開啟 Claude Code，安裝 plugin。交接功能可直接使用。
2. 可用 setup 安裝 handoff 規則、agent 分派或兩者。要只啟用角色分派，執行 `/cc-feather:setup 在目前專案只安裝 agent 分派規則與角色`；若要跨專案使用，明確改成「在使用者範圍安裝」。完成後開新 session。
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
| 事實查找 | scout | haiku | low |
| 廣域探索 | Explore | haiku | low |
| 分析／安全分析／計畫審查 | analyst | opus | high |
| 機械式實作 | mech-executor | sonnet | medium |
| 一般工程實作 | executor | opus | medium |
| 安全敏感實作 | security-executor | opus | high |

| 角色 | 何時使用 | 產出與權限 |
| --- | --- | --- |
| scout | 範圍明確的事實查找，例如定位定義、設定或引用 | 唯讀；回報檔案位置與證據，不做複雜因果分析 |
| Explore | 尚不清楚程式結構，需要較廣的模組、入口、呼叫關係探索 | 唯讀；建立理解程式的地圖，深入診斷交給 analyst |
| analyst | 根因／影響分析、安全問題查找、實作前計畫審查 | 唯讀；回報證據、推論與建議；計畫審查回覆 READY／REVISE |
| mech-executor | 規則、範圍與結果已明確的重複修改 | 可修改指定檔案；按完整規格執行，例如批次改名 |
| executor | 需要局部設計與工程判斷的功能或修正 | 可修改指定檔案並驗證，遇到架構或需求缺口交回主 Agent |
| security-executor | 影響授權、秘密資料、密碼學或信任邊界的實作 | 可修改指定檔案；驗證正常行為及濫用／拒絕案例 |

主 Agent 保留需求理解、決策、整合與最後驗收。小型或脈絡高度耦合的工作直接處理；獨立子任務才分派，明確指定範圍、檔案 ownership 與完成條件。子 Agent 都是 leaf，不再往下分派。

每個欄位獨立套用優先序：**該次任務明確指定 > 適用的 session 指定 > 已儲存角色設定 > 套件預設**。例如「用 Sonnet 審查計畫」仍使用 analyst 職責，model 改為 Sonnet，未指定 effort 則保留 analyst 的 high。指定值無法原生套用時先說明，不暗中替換或只在 prompt 假裝設定成功。

安全分析由唯讀 analyst 做；涉及實際安全邊界的實作交給 security-executor。自動計畫審查可依任務／session 明確啟用或停用；預設關閉；開啟後依實質風險觸發，明確要求審查則不受開關限制，使用新 analyst context；預設自動最多兩次（包含初審），第二次仍有阻礙則停止自動送審。上限不是自動通過，改名／換模型／新 session 不重置。有既存交接時保存輪數與阻礙；超過上限需要使用者明確要求。READY 且已有授權就繼續，不固定再問一次批准。

### 自動計畫審查開關

```text
/cc-feather:auto-on
/cc-feather:auto-off
/cc-feather:auto-on project
/cc-feather:auto-off user
```

不帶參數（或加 `session`）只影響目前 session；加 `project` 或 `user` 則永久儲存至該範圍既有的 setup 安裝。保留 Claude plugin 的 `cc-feather:` 命名空間，指令名稱不再重複 `feather-`。

預設 `off` 不自動觸發；開啟後的 `auto` 僅按實質風險觸發；兩者都接受明確要求的審查。永久設定不會取消另行指定的單次／session 偏好。可用 setup 查詢已儲存模式；更新保留永久選擇，切換不重置既有計畫的審查次數。

永久模式儲存位置如下；請透過指令修改，避免手動編輯管理區塊造成擁有權衝突。

| 範圍 | 載入給 Claude 的政策 | 同步管理狀態 |
| --- | --- | --- |
| project | `<專案>/CLAUDE.md` | `<專案>/.claude/cc-feather/state.json` |
| user | `<Claude 設定目錄>/CLAUDE.md` | `<Claude 設定目錄>/cc-feather/state.json` |

Claude 設定目錄預設是 `~/.claude`，可由 `CLAUDE_CONFIG_DIR` 指定。管理區塊的 `Automatic plan review mode: off` 表示關閉，`auto` 表示開啟。永久開關需要先安裝該範圍的 agent 分派；只有 handoff 規則不夠；專案設定可能優先於使用者設定，新 session 載入已儲存模式。開啟後只對安全邊界、資料遷移、不可逆操作或複雜跨模組計畫等實質風險觸發，不會每個任務都送審。

### Explore 的成本控制

內建 Explore 會繼承主模型；只新增 plugin scout 無法防止它被呼叫。Setup 因此部署**真正名為 Explore 的原生角色**，明確寫入 haiku/low。遇到既有自訂 Explore 會保留並回報衝突，不直接覆蓋。

儲存值不是實際執行證據：CLI／managed／巢狀專案定義、模型 force 變數、provider allowlist 或單次參數可能影響模型。Setup 後用新 session，執行探索時以 `/tasks` 核對實際 model／effort。模型選擇降低的是意外使用昂貴模型的成本，不保證 token 數下降。參考 [Claude subagents](https://code.claude.com/docs/en/sub-agents)。

## 交接相容性

```text
/cc-feather:handoff 保存目前工作
/cc-feather:handoff 列出目前交接
/cc-feather:handoff 讀取登入功能交接
/cc-feather:handoff 接續登入功能
/cc-feather:handoff 搜尋提到登入的完成紀錄
```

沿用 [codex-feather](https://github.com/xenciscbc/codex-feather) 的 `.feather/handoffs/<work>.md`、`history.md` 與 `archive/<batch>.md`。讀取不接續執行；接續核對來源後繼續已授權工作。完成自動歸檔，失敗保留可重試資料；清除與封存需要明確範圍。來源基準只涵蓋選定檔案，不代表測試通過。明確指定 Claude memory 才做外部記憶唯讀查找。

Claude 與 Codex 需使用同一個專案目錄並協調單一寫入者；無跨 session 交易鎖或 worktree 自動同步。交接工具依原有規則處理 Git 忽略與使用者追蹤選擇。

## 更新、移除與驗證

Plugin 更新只更新套件，需另跑 setup update 更新選定的已部署項目；移除 plugin 不會自動刪除外部角色／政策，請先移除想清理的 setup scope。使用者修改過的管理檔會保留為衝突，交接紀錄不刪除。

```text
/cc-feather:setup 更新目前專案已安裝的角色與指引，保留模型與審查模式
/cc-feather:setup 移除目前專案由 cc-feather 管理的角色與指引
```

若先前安裝在 user 範圍，請明確指定更新／移除使用者範圍。移除角色與指引後，再透過 Claude 的 plugin 管理介面解除安裝套件。

[交接相容性驗證](docs/compatibility.md)記錄原有測試；新增 setup/model 的測試與限制見[設定驗證](docs/setup-validation.md)。設定與政策檔案檢查不等於已驗證真實 Claude 派工。計畫審查輪數與派工條件是模型指引，沒有 hook 強制計數；本套件不以設定成功宣稱 live model 已確認。

## Agent 名稱與舊版升級

原生名稱直接使用 `scout`、`analyst`、`mech-executor`、`executor`、`security-executor`、`Explore`，不再有 `feather-` 前綴。

Setup 遇到既有同名角色（即使位於不同檔名或子目錄），會列出衝突並保留檔案，請使用者決定保留既有配置、將既有角色改名，或備份後替換；取得具體選擇前不覆蓋或接管。跨 user/project 範圍的同名角色依 Claude 優先序生效，需一併核對適用範圍。

舊版已管理的 `feather-*` 角色請執行 `/cc-feather:setup 更新目前專案的角色與指引`（user 安裝請指定使用者範圍）。Update 會預覽更名、保留 model／effort 及審查模式，只有完整且未被修改的舊角色才遷移；新名稱已被占用就停止。完成後開新 session。Model、永久審查開關與 session 匯出需先完成遷移；也可直接移除完整的舊版管理安裝。
