# Pilotfish 的 agent 角色與開發流程介入

研究日期：2026-09-23。核對 GitHub main commit `4b35ad6ef0de7b1e3966c2b96f05c99af4aba702`；根目錄 VERSION 為 1.4.1。這是原始碼與文件調查，未安裝或實跑 Pilotfish。

## 結論

Pilotfish 把主 Agent 的決策責任、子角色的模型／能力與開發流程政策分開。主 Agent 負責需求定義、架構、計畫、授權協調、整合與最後驗收；子角色只做有邊界的工作。它同時設計了避免過度分派的 dispatch brake，以及依風險啟動的前後兩道獨立審查。這些是政策要求，不能等同於每個 session 都會自動遵守的執行保證。

## 角色

| 角色 | 模型／effort | 工作與能力 |
| --- | --- | --- |
| 主 session | 安裝預設 opus；既有選擇另有保留規則 | 需求、計畫、決策、整合與最終判斷 |
| scout | haiku / low | 有界事實查找，僅 Read、Glob、Grep |
| Explore | haiku / low | 廣域搜尋；legacy 全域版本覆寫內建角色 |
| plan-verifier | opus / medium | 實作前檢查計畫；僅 Read、Glob、Grep；READY 或 REVISE |
| security-reviewer | opus / high | 批准前安全分析；可讀檔與查網頁，無 Bash 或寫入工具 |
| mech-executor | sonnet / low | 規格已完整決定的機械式修改 |
| executor | sonnet / medium | 有明確邊界、但需要局部設計判斷的實作 |
| security-executor | opus / high | 已批准的安全敏感實作 |
| verifier | opus / medium | 實作後以新 context 重現驗收與反例；CONFIRMED、REFUTED、INCONCLUSIVE |

來源：[角色定義目錄](https://github.com/Nanako0129/pilotfish/tree/4b35ad6ef0de7b1e3966c2b96f05c99af4aba702/templates/agents)。各角色的 model、effort 由 frontmatter 設定；policy 要求呼叫命名角色時省略 model，以免蓋掉角色綁定。全部子角色都是 leaf，不再產生子代理；寫入角色以 disallowedTools 排除 Agent、Workflow，唯讀角色則用正向工具清單限制能力。

## 從需求到交付

1. 先判斷互動型態：結果或驗收不清楚是 co_discover；方向清楚但範圍大／影響高是 explore_then_plan；清楚且有界是 execute。explore_then_plan 第一回合只讀調查，完成可供批准的計畫後結束該回合，等下一回合明確批准。
2. 評估是否值得分派：範圍、問題、輸出、停止條件要穩定；單一未知 bug 的診斷與第一個修正通常由主 Agent 持續完成，避免 scout 接 executor 的接力丟失脈絡。
3. Discovery 可以把獨立查找交給 scout；主 Agent 回收證據並形成 Plan。大型工作有總體 envelope 與可分別批准的 slices，各自列出範圍、owner、先決條件、驗收、回復方式、預算與停止條件。
4. 有獨立審查觸發條件時，先由 plan-verifier 審查穩定計畫，READY 後再交使用者批准。安全工作更早先經 security-reviewer，將其發現與處置帶進計畫，再交 plan-verifier；兩項批准前審查不並行。
5. 批准後依工作性質交給 mech-executor、executor 或 security-executor。任務 brief 包括目標、限制、檔案範圍、完成條件與理由；寫入範圍有專屬 owner。
6. 先跑主要驗收，再在完整且可反駁成果主張的整合邊界，由 fresh-context verifier 獨立驗證。測試不能取代獨立審查，獨立審查也不能取代測試。
7. 主 Agent 判斷 findings，採 FIX、DEFER、REJECT，並對最後交付負責。審查結論不是新增範圍或執行外部操作的授權。

獨立審查觸發條件包含使用者指定獨立審查、安全／信任、不可逆／外部變更、資料或 schema／序列化／migration、發布及重要跨元件驗收。不是單靠檔案數決定。小型、穩定、低風險工作可留在主 session。

來源：[流程政策](https://github.com/Nanako0129/pilotfish/blob/4b35ad6ef0de7b1e3966c2b96f05c99af4aba702/templates/claude-md.orchestration.md)。

## 審查及執行限制

- plan-verifier 不代寫計畫，REVISE 需附 blocker、證據、最小修訂、驗收方式；只以實質 P0–P2 缺陷阻擋。來源：[plan-verifier](https://github.com/Nanako0129/pilotfish/blob/4b35ad6ef0de7b1e3966c2b96f05c99af4aba702/templates/agents/plan-verifier.md)。
- verifier 可執行測試，不能編輯／修復；工具排除 Write、Edit、NotebookEdit，但 Bash 仍可用。因此其「不改動」不能解讀為作業系統層唯讀 sandbox。這是從 capability 清單得到的限制判讀。來源：[verifier](https://github.com/Nanako0129/pilotfish/blob/4b35ad6ef0de7b1e3966c2b96f05c99af4aba702/templates/agents/verifier.md)。
- 並行寫入用 Git worktree 隔離；無 Git 不啟動多個並行 writer。長命令由主 session 追蹤，leaf 不自行 detach。修正／重審需有實質新變化，不反覆重驗相同狀態。來源：[流程政策](https://github.com/Nanako0129/pilotfish/blob/4b35ad6ef0de7b1e3966c2b96f05c99af4aba702/templates/claude-md.orchestration.md)。

## 對 cc-feather 的意義（設計判斷）

可借鏡的是把「角色能力」、「何時分派」、「驗收與批准」、「如何啟動規則」分開維護。若未來擴充 sub-agent，不只新增 agents/*.md，還要決定流程介入程度：是輕量委派指引，或 Pilotfish 這種會要求新一回合批准、風險審查與停止條件的完整政策。這次研究未修改 cc-feather 的 skill 或新增 sub-agent 功能。

## 啟動機制（已整合獨立查核）

舊版在全域 CLAUDE.md 放 policy，agents 放角色，settings 設主模型。Plugin beta 則註冊 SessionStart hook，matcher 為 startup|resume|clear|compact，呼叫 emit-sessionstart.sh；通過配置／舊版相容性檢查才輸出 sessionstart.txt，讓政策進入主模型上下文。這不是每次工具操作的批准攔截器，該 hooks.json 沒有註冊 PreToolUse。角色工具清單與模型是否遵守派工政策須分開看。

主 Agent 已另行核對 pinned [hooks.json](https://github.com/Nanako0129/pilotfish/blob/4b35ad6ef0de7b1e3966c2b96f05c99af4aba702/plugin/hooks/hooks.json) 與 [emit-sessionstart.sh](https://github.com/Nanako0129/pilotfish/blob/4b35ad6ef0de7b1e3966c2b96f05c99af4aba702/plugin/hooks/emit-sessionstart.sh)，確認事件 matcher、環境檢查與 cat 輸出機制。詳細啟用路徑、可選手動 skill、平台限制見 [啟用機制查核](pilotfish-activation-research.md)。Plugin 使用七個 namespaced 角色，不包含 legacy 的 Explore 覆寫；上表八個子角色須依安裝型態理解。

分工：主 Agent 查角色與 lifecycle；analyst 查 activation/hooks，原始碼唯讀，僅產生指定研究文件。analyst 原生呼叫參數為 gpt-6-sol / high（AGENTS 角色預設）；沒有獨立可見的實際模型執行證據。未執行安裝、設定變更或行為測試。
