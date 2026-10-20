# cc-feather 參考

[English](reference.md) | **繁體中文**

[README](../README.zh-TW.md) 提供概覽與設計取捨；這份文件說明每條分派規則的用途與適用時機，並連到寫明該規則的流程或審查狀態項目。每條規則只寫一次，寫在負責它的檔案裡，主 Agent 依循的是那些檔案，不是這份文件（[ADR 0017](adr/0017-each-delegation-rule-is-written-once.md)）。這份文件也說明這個流程的限制，以及仍由你承擔的風險。名詞定義見 [CONTEXT.md](../CONTEXT.md)。

## 自動審查

審查步驟、負責角色與各步驟的通過條件見 README 的[分派與預設模型](../README.zh-TW.md#分派與預設模型)。

規則寫在哪裡：分派對象、派工、安全關鍵變更的定義，以及接收或補救子 Agent 的結果，寫在[分派 skill](../skills/delegation/SKILL.md)；各審查步驟共用的狀態，例如次數、停止門檻、有效範圍、完成標準、commit、最終檢查、你的決定、恢復的 session 與派工紀錄，寫在[審查狀態規則](../skills/delegation/references/review-state.md)；各步驟自己的規則寫在[計畫審查](../skills/delegation/references/plan-review.md)、[程式碼審查](../skills/delegation/references/code-review.md)、[結果驗證](../skills/delegation/references/outcome-verification.md)與[對抗式審查](../skills/delegation/references/adversarial-review.md)程序，預覽的規則寫在[預覽流程](../skills/delegation/references/preview.md)。下文的「審查狀態規則的 Reading set」指審查狀態規則中以該名稱粗體開頭的項目。主 Agent 在任何依賴審查狀態規則的決定或 brief 之前，會完整讀過審查狀態規則，如其中的 Reading it 所說。

- **沒有計畫的工作**不自動審查：這個流程是為了依你同意的計畫施工的工作。出錯後難以挽回的工作，也就是安全關鍵變更、資料遷移或不可逆操作，須先寫出計畫、通過審查並經你同意才施工，所以風險最高的工作不會在沒有計畫時開始。規則寫在[計畫審查程序](../skills/delegation/references/plan-review.md)。
- **依 claim 審查的時機：**在 auto 下，每個 claim 一實作完成並 commit 就接著審查與驗證，不等整份計畫實作完，所以早期 claim 的問題會在後面的 claim 建立在它之上之前被發現。這是 auto 唯一的審查時機，而同一個工作樹裡的審查仍與實作輪流進行，如「審查依序進行」所說。規則是審查狀態規則的 Per-claim timing。
- **相依的 claim：**在 auto 下，依 `Blocked by` 行或計畫本身的順序依賴另一個 claim 的 claim，要等那個 claim 通過才開始，所以它不會建立在審查還可能改變的工作上；沒有這種相依的 claim 不必等待。它所依賴的 claim 停下或沒有你的決定就無法通過時，它也跟著停下，由你決定，你也可以讓指定的相依 claim 繼續。規則是審查狀態規則的 Dependent claims。
- **固定的通過：**在 auto 下，已通過的 claim 不會因另一個 claim 的改動而重新打開，只要那項改動經過那個 claim 自己通過的審查，所以後面的 claim 碰到前面的檔案時，不會讓計畫重跑一輪審查；這項改動造成的問題，由做出改動的 claim 修正。沒有經過通過的審查的改動仍會重新打開；在 `off` 下，改動 claim 的檔案一律會重新打開它；claim 只有在自己的閱讀範圍寫明時，才能改動另一個 claim 的驗收檢查。規則是審查狀態規則的 What a pass covers。固定的通過有其限制：後面 claim 的 reviewer 只讀它自己的閱讀範圍，可能不知道前面 claim 的設計用意；前面 claim 的某項性質，若沒有任何最終檢查執行的驗收檢查涵蓋，就可能被破壞而最終檢查沒有發現。
- **次數上限：**每個步驟連續沒通過的自動呼叫達到[停止門檻](#停止門檻)（預設 2）時就停下，所以一直失敗的流程會等你，而不會無止境地重試；停下絕不等於通過。計畫審查以計畫計，其他步驟以 claim 計，每次嘗試的呼叫都算一次，同一 session 內改名、換 reviewer 或換模型都不會讓次數歸零；恢復的 session 重新計數。規則是審查狀態規則的 Transitions、What counts as a call 與 What does not reset a count，各程序計數的步驟也說明它自己的 INCONCLUSIVE 怎麼算。
- **施工中的重審：**你同意的內容改變時，也就是重大偏離，或發現計畫缺少的安全控制或不變條件時，才會重審計畫，所以實作不會跑在同意的計畫前面；受影響的後續工作會等修訂後的計畫通過審查並經你同意。措辭調整或在已同意的結果、範圍與驗收條件內的修改，不會重審計畫；相關程式碼仍隨所屬 claim 經過程式碼審查與驗證。規則是[計畫審查程序](../skills/delegation/references/plan-review.md)的第 5 步，以及審查狀態規則的 Deviations 與 Deviation scope。
- **問題分級：**審查只會因為 claim 還沒完成而擋下它：驗收條件照所寫的內容沒有達成、既有行為被破壞、引入安全問題或資料遺失，或偏離計畫。這讓審查不會用 claim 範圍以外的問題擴大工作，而安全問題與資料遺失不論驗收條件怎麼寫都會擋下。不是這兩者的既有行為破壞，要有失敗的測試或重現步驟，其他問題都記下來留待之後。兩種模式、每位使用者都用同樣的標準，沒有可以調整它的設定。標準是審查狀態規則的 Completion criteria；各步驟如何處置問題寫在它的程序裡。
- **後續紀錄：**一份工作的非阻擋問題保存在一份紀錄裡，所以工作完成時不會遺失，也能成為你選擇開始的之後計畫的依據。它只是資料：下一步永遠是由你決定要不要開始之後的計畫，其中引用的問題都標為不可信，讀取或接續它都不代表任何授權，接受並合併也從不依據它。之後的計畫不會自動開始；修正已記錄問題的新計畫，照一般規則算是新的工作。主 Agent 依任何問題提出或採用一項要求或修正之前，會先權衡這個情況何時會發生、最壞而可信的後果，以及既有規則是否已經涵蓋，所以少見的邊緣情況不會增加規則；這項權衡從不改變什麼會擋下。紀錄是審查狀態規則的 Follow-up record，權衡寫在[分派 skill](../skills/delegation/SKILL.md)。
- **未通過：**把關讓還沒通過的工作不進入預設 branch、不 release、不回報完成：沒拿到 APPROVED 的 claim 視為未審查，沒有有效 CONFIRMED 的視為未驗證，安全關鍵 claim 還要有有效的 HELD。claim 受把關期間，進行中的交接會記下它還缺什麼，所以單一通過（例如 `off` 下明確要求的審查）絕不會讓 claim 進入預設 branch。唯一例外是你決定接受並合併（見你的決定）。規則是審查狀態規則的 Commit and completion 與 Pending acceptance；REFUTED 或 BROKEN 之後怎麼做，寫在[結果驗證](../skills/delegation/references/outcome-verification.md)與[對抗式審查](../skills/delegation/references/adversarial-review.md)程序。
- **有效範圍：**通過只對它審過的內容有效，所以之後的改動無法沿用先前的通過：改動 claim 的檔案或其相依項目，會重新打開它的程式碼審查與驗證；改動環境會重新打開驗證；安全關鍵 claim 的測試目標，或與它共用安全假設的內容有改動時，會重新打開 HELD。重新打開的步驟接續它的次數，不會從零開始。規則是審查狀態規則的 What a pass covers 與 Reopened calls；共用安全假設的變更組合後版本的審查，是[對抗式審查程序](../skills/delegation/references/adversarial-review.md)的第 9 步。
- **Commit 條件：**在 auto 下，主 Agent 可以不經詢問，在 claim 通過前先 commit，推到它為這項工作建立的 branch，並開 PR 列出尚未驗收的 claim，所以每次審查都針對一個具名的 commit，進行中的工作也不會遺失。進入預設 branch、release、回報完成與把 ticket 設成完成，仍要等審查通過或你決定接受並合併。要推到不是它建立的 branch 前會先問你，開 PR 不等於可以 merge，你明確說不要 commit 或不要 push 時，以你的指示為準。每個 commit 只包含 claim 的檔案，由主 Agent 以名稱加入並 commit，所以你先前 stage 的內容不會進入其中。規則是審查狀態規則的 Commits before the passes、Repository authority 與 Commit and completion。
- **事後檢查：**只有在授權操作之後才會存在的驗收項目（例如 commit 之後的 tag），無法在操作前驗證，所以由主 Agent 在操作後檢查並回報；其餘部分在操作前驗證。規則是審查狀態規則的 Postconditions。
- **審查依序進行：**審查判斷的工作樹在它執行期間不會被其他東西改動，所以它的結論針對的就是它指名的 commit；因此在同一個工作樹裡，審查與實作輪流進行，呼叫期間 claim 依賴的檔案有變動時，該次呼叫的通過不予採用。主 Agent 不會自行為審查建立 worktree，因為建立 worktree 可能要重新安裝相依套件或重新建置專案。你分開在不同 worktree 進行的工作可以平行。規則是審查狀態規則的 Serial within a working tree。
- **最終檢查：**進入預設 branch 或 release 之前，主 Agent 會在要進入預設 branch 的 commit 上執行計畫的整體驗收檢查（例如完整測試），這是它自己的執行，遵守[審查狀態規則](../skills/delegation/references/review-state.md)中的 Execution 規則。這樣各自通過的 claim 也會一起檢查，在 auto 下還會在那裡重跑每個 claim 的主要驗收。它不是審查步驟，也不產生結論；失敗由歸因的 claim 修正，或由主 Agent 加入的修正用 claim 修正，進入預設 branch 要等它通過或你決定接受並合併。不允許執行儲存庫程式碼時，這項檢查會記為未執行，主 Agent 會在進入預設 branch 之前，以及任何接受並合併的決定中告訴你。修正用的 claim 若改動安全控制，就屬於安全關鍵，但主 Agent 仍不先問你就加入：它沒有計畫審查、安全分析或對抗式審查，主 Agent 會在最後揭露它，附上問題與修正摘要，由你決定是否帶著它合併。規則是審查狀態規則的 Final check。檢查不會在最後的 commit 上重做所有事：claim 主要驗收以外的驗收項目不會重跑，無法重跑的驗收檢查（例如手動檢查）也不會重做。檢查所執行的儲存庫程式碼掌控自己的輸出，所以它可以讓該失敗的檢查通過、隱藏檢查少跑了測試，或讓失敗指向錯誤的 claim；最後這種只會讓修正找錯對象，修正之後檢查會再執行一次。
- **你的決定：**步驟等你決定時，主 Agent 會把你的決定記為重審、延後、取消、修改驗收、豁免或接受並合併其中一種，並註明範圍，所以一個決定只涵蓋它寫明的內容。豁免會連同剩餘風險持續列出，絕不算通過。接受並合併是你明確接受某個 claim，即使它缺少一關或兩關，或缺少 HELD，並記下所接受的 commit、缺少的關卡與剩餘風險；之後若有相關變更就失效。你說工作已完成，要等主 Agent 向你確認並記為接受並合併，才算驗收；說「繼續」或關掉 auto，都不代表接受已知的缺陷。規則是審查狀態規則的 User decisions。
- **最後一次決定接受並合併：**主 Agent 只問你一次接受並合併的決定：在計畫的每個 claim 都完成審查、最終檢查已執行或記為未執行之後，進入預設 branch 或 release 之前，所以你是看著整份計畫決定，而不是一個 claim 一個 claim 決定。在 auto 下，即使沒有 claim 需要你決定也會問，清單寫明最終檢查的狀態、每個 claim 的通過、缺少的關卡與未解決的阻擋性問題、每個安全關鍵 claim 的對抗式審查結果、每個安全關鍵的修正用 claim、後續紀錄，以及這個流程不檢查的事項。你可以以整個 claim 為單位只確認清單的一部分；說「繼續」、沒有回應或關掉自動審查都不算確認，這個決定也只涵蓋清單上列出的內容。規則是審查狀態規則的 Accept and land at the end of the plan。這個流程不檢查的事項是：後面 claim 的審查者只讀自己的閱讀範圍，可能不知道前面 claim 的設計意圖；沒有任何重新執行的驗收檢查涵蓋的前面 claim 特性，可能被破壞而最終檢查不會發現，主要驗收以外的驗收項目也不會在最後的 commit 上重新執行；無法重新執行的驗收檢查（例如人工檢查）不會在最後的 commit 上重做；對抗式審查攻擊的 commit 並沒有被 claim 自己的程式碼審查與驗證整體審過；對抗式審查的發現不在這份計畫中修正；安全關鍵的修正用 claim 不經過對抗式審查；以及主 Agent 照派工紀錄所寫的內容採信，所以修改它就會改變主 Agent 相信的內容。你在這個決定中選擇的重審可以補回其中一部分。
- **授權：**通過不代表新的授權；READY 且原本已有授權的工作直接繼續，不固定再問一次。規則是[計畫審查程序](../skills/delegation/references/plan-review.md)的第 5 步與審查狀態規則的 Repository authority。
- **明確要求**計畫審查、程式碼審查、驗證或對抗式審查（包括 `/cc-feather:adversarial-review`）時不受開關限制，所以你隨時都能要求審查；它只執行你要求的那一項，不計入次數，也不會讓任何步驟的次數歸零。在 auto 下，若它讓自動流程已停下的步驟通過，自動流程會從那裡接續。規則是審查狀態規則的 What an explicit call runs 與 Clearing a stop。
- **停下之後：**已停下的步驟明確通過時，停止狀態解除，但次數不變，所以同一份工作在該步驟之後的自動呼叫（例如修正後的審查），在次數大於或等於停止門檻時仍需要你要求；停下就是為了讓你參與。規則是審查狀態規則的 Clearing a stop 與 Next automatic call。
- **要求審查時：**在 auto 下，你要求的審查算自動或明確，取決於流程是否正該跑那個步驟，主 Agent 派出前會先說明是哪一種，因為這決定它怎麼計數。規則是審查狀態規則的 Classifying a request。
- **實作完才做計畫審查：**在 auto 下，工作已經實作，但這個 session 沒有它的計畫審查紀錄，例如在另一個 session、Claude 以外或 review 為 off 時實作的，主 Agent 會在任何審查前先問你：要先補計畫審查，還是直接做程式碼審查，所以略過計畫審查是你的選擇。直接做程式碼審查會把缺少的 READY 記為豁免，但不會豁免安全分析。規則是審查狀態規則的 Implemented before plan review。
- **重試：**每次嘗試的呼叫都算一次，包括暫時失敗後的一般重試，所以重試無法繞過停止門檻；派出前就發現角色或新 context 不可用，不算一次呼叫。規則是審查狀態規則的 What counts as a call 與[分派 skill](../skills/delegation/SKILL.md) 的 Accept or recover。
- **狀態不明：**這個 session 中無法確定次數、結論或阻擋事項時（例如 context 壓縮後；壓縮不算新的 session），主 Agent 會視為已停下並問你，而不是用猜的。每次審查結果都會附上目前的次數。規則是審查狀態規則的 Unknown state。
- **派工紀錄：**在 auto 下，計畫的審查狀態透過每份計畫一份、放在 `.feather/dispatch/<name>.md` 的紀錄帶到新的 session，所以新的 session 或 context 壓縮後的主 Agent，不會重新審查已通過的工作，也不會再問它記有 READY 的已實作工作。它不保存次數、攻擊細節或機密，主 Agent 也讓它不進 Git。次數仍在每個 session 重新計算，主 Agent 也會在進入預設 branch 前重新執行最終檢查。在 `off` 下，主 Agent 不寫派工紀錄。規則是審查狀態規則的 Dispatch record。主 Agent 照紀錄所寫的內容採信，所以有人或審查、最終檢查執行的儲存庫程式碼修改它，就會改變主 Agent 相信哪些通過與結果；cc-feather 不防範這一點。
- **成本：**在一個 session 內一次不中斷的完成過程中，停止門檻為 K 時，一份有 N 個 claim、其中 S 個是安全關鍵 claim 的計畫，至少自動呼叫 1 + 2N + S 次，最多約 K³ + K(K+1)N + KS 次，因為每個 claim 最多 K(K+1) 次（最多 K 次驗證，其間最多 K − 1 次修正各最多 K 次程式碼審查，再加上第一次驗證前最多 K 次程式碼審查），安全關鍵 claim 最多 K(K+1) + K 次（再加上最後一次執行的最多 K 次對抗式審查，那裡的 BROKEN 只記錄、不修正），計畫審查與最終檢查的修正合計最多 K³ 次（最多 K 次計畫審查，加上最終檢查停下前連續最多 K − 1 次修正，每次修正在造成失敗的 claim 或修正用的 claim 中最多 K(K+1) 次程式碼審查與驗證）。預設 K = 2 時，一次不中斷的完成過程中每個 claim 最多 6 次、安全關鍵 claim 最多 8 次，整份計畫約 8 + 6N + 2S 次；K = 10 時則是 110 次、120 次與約 1000 + 110N + 10S 次。因為每次修正都要重新審查與驗證，上限增加得比 K 快。有安全關鍵 claim 的計畫，還會對每份計畫或共用的信任邊界做一次安全分析；重新打開的 claim、最終檢查的修正與每次經你同意的重大偏離都會再增加呼叫；預設角色都是 opus/high。你在最後的決定中選擇重審時，選擇的審查會再增加呼叫，若重審改動了程式碼，最終檢查也會再執行。要降低成本，維持較低的停止門檻，或用 `/cc-feather:model` 調整角色，例如 `verifier.effort=medium`；package 預設不變。計畫要切成多細的 claim，由寫計畫的地方決定（例如 spec、規劃或切票的 skill），不是 cc-feather。預覽如何列出這些上限，寫在[預覽流程](../skills/delegation/references/preview.md)。
- **獨立性：**每次審查都在新的 context 中自行取得證據，但通常和主 Agent 用同一個模型。想要模型多樣性，可用 `/cc-feather:model` 把 analyst 或 reviewer 設成其他模型。cc-feather 看不到也無法保證主 Agent 的模型；換角色模型不會讓該步驟的次數歸零。若你有其他廠商的模型，可另外明確要求第二意見，它不屬於這個流程。

**哪份文件是計畫。**計畫就是你要求主 Agent 實作時指名的那份文件；指名即代表你同意它，指名什麼也決定了它有哪些 claim。這些規則是給主 Agent 的指示，沒有任何工具強制執行；測試只確保各文件說法一致。它們寫在[計畫審查程序](../skills/delegation/references/plan-review.md)的計畫辨識與 spec 檢查清單，以及審查狀態規則的 Reading set、Ticket status、Claim changes、Deviation scope、Spec updates 與 Conversation plans。

- **一份 spec：**你指名的 spec 就是計畫，除非它自己列了 claim，否則就是一個 claim。它還有未完成的 ticket 時，主 Agent 會先問你要實作 spec 本身還是它的 ticket，因為答案決定審查什麼、有幾個 claim。
- **一份 spec 的 ticket（全部或部分）：**你指名的 ticket 是一份計畫，只做一次計畫審查，所以該放在一起的 ticket 會一起判斷；每張未完成的 ticket 是一個 claim，它的 `Blocked by` 行就是相依關係。
- **單一 ticket：**單獨指名的 ticket 就是計畫，也是它唯一的 claim，計畫審查仍會拿它對照它的 spec。
- **不屬於任何 spec 的 ticket**（沒有 `Spec:` 行、parent 參照或同一個目錄把它連到某份 spec，你也沒有把它指名為某份 spec 的 ticket）自成一份計畫，不做檢查清單：指名它就代表你同意它。你指名為某份 spec 的 ticket，就是那份 spec 的 ticket，如「辨識 ticket」所述。**沒有 ticket 的 spec** 沿用它列出的 claim，或整份是一個 claim，前提是它有自己的範圍與驗收條件。
- **例子：**`docs/specs/login.md` 有尚未完成的 ticket 01、02、03，且 03 `Blocked by` 02。「實作 login spec」時主 Agent 會先問你：答「ticket」是一份有三個 claim 的計畫，計畫審查一次，03 等 02 完成；答「spec」則整份 spec 是一個 claim。「實作 ticket 02 和 03」是一份有兩個 claim 的計畫。在新 session 中「實作 ticket 02」，則 ticket 02 是計畫，也是它唯一的 claim，它的審查讀 ticket 02 與它引用的 `login.md` 部分。沒有 ticket、也沒有列 claim 的 `docs/specs/logout.md`，指名它就是一個 claim。
- **spec 作為檢查清單：**計畫是某份 spec 的 ticket 時，計畫審查把 spec 當作檢查清單，而不是計畫的一部分，讓 ticket 留在 spec 的範圍內，引用適用於它的決定、安全不變條件與 Out of Scope 條目，並在全部指名或完成時涵蓋 spec 的結果。缺少涵蓋或引用都是阻擋事項。
- **引用：**引用指向 spec 中的一個部分，例如段落、編號項目或 `S2` 這類識別碼，所以 ticket 的審查只讀適用於它的內容，而不是整份 spec；`Spec:` 行不算引用，引用無法對應到恰好一個部分時，在計畫審查就是阻擋事項。
- **審查讀什麼：**claim 的實作者與它的程式碼審查、結果驗證與對抗式審查讀同一組閱讀範圍，也就是 claim 所寫的文字與它引用的 spec 部分，所以每個步驟都依同一份文字判斷這個 claim，這份文字改變時也會被發現。安全關鍵 claim 的 brief 帶的是它自己的安全不變條件與測試目標，不是其他 claim 的。ticket 在這個 session 沒有它的計畫的 READY 就被實作或審查時，它的閱讀範圍是整份 spec。這些是給模型的指示：角色仍可能打開整份 spec 檔案，只有它的 brief 讓它停在被引用的部分。
- **檢查清單的限制：**檢查清單在計畫審查時執行，看的是當時寫下的 spec 與 ticket；涵蓋檢查只在指名與已完成的 ticket 就是 spec 的全部 ticket 時執行；spec 不是 claim 的驗收條件，所以計畫審查之後，ticket 的各項審查只讀該 ticket 與它引用的 spec 部分，但在這個 session 沒有它的計畫的 READY 就被實作或審查的 ticket 會讀整份 spec，如「審查讀什麼」所述；這些規則是給模型的指示，沒有任何工具強制執行。
- **已涵蓋：**這個 session 已有計畫涵蓋你指名的工作時，就沿用該計畫，保留它的次數、結論與阻擋事項，所以指名單一 ticket 既不會重複審查，也無法繞過已停下的審查。
- **部分重疊：**新計畫與這個 session 既有的計畫重疊時，重疊的工作承接既有計畫尚未解決的結論與阻擋事項，以及它停下時的次數與停止狀態，所以重疊的工作無法繞過停止。規則是審查狀態規則的 Overlap。
- **恢復的 session：**哪些內容帶到新的 session，決定了那裡要重新審查什麼。次數絕不會帶過去，已完成的 ticket 也不會重做。在 auto 下，通過、對抗式審查結果、未解決的結論與你的決定透過派工紀錄帶過去；在 `off` 下，通過的結論不會帶過去，只有進行中的交接會帶過未解決的結論，所以之前 session 通過的 claim 在進入預設 branch 前要重新審查，除非它的 ticket 顯示它已驗收。規則是審查狀態規則的 Resumed sessions。
- **沒有剩餘工作：**指名範圍內的 ticket 都已完成時，主 Agent 會回報沒有剩下要實作的部分。
- **Ticket 狀態：**claim 通過（兩關，安全關鍵 claim 還要加上 HELD）並 commit 之後，或你決定接受並合併之後，主 Agent 會把它的 ticket 設成你的 tracker 慣例定義、表示已完成的值，所以已完成的 ticket 不會重做；在 auto 下，要等你對計畫做出最後決定之後。完成只代表不再重做：表示不會做的值（例如 `wontfix`）絕不算驗收。規則是審查狀態規則的 Ticket status。
- **辨識 ticket：**主 Agent 依明確連結（例如 `Spec:` 行或 parent 參照）、同一個功能目錄，或你直接指名，來辨識 spec 的 ticket，並先看專案指示有沒有寫 ticket 放在哪裡。全 repo 搜尋可能跳過版本控制忽略的檔案和隱藏目錄，所以搜不到不代表沒有。你指名的內容對不上任何計畫或對上多份時會詢問，並說明實際採用了哪些 ticket。
- **告訴主 Agent ticket 放在哪裡：**在專案的 CLAUDE.md 或 AGENTS.md（或它們指向的檔案）寫一行，說明 spec 和 ticket 放在哪裡，例如「Tickets: `.scratch/<feature>/issues/`, linked to specs in `docs/specs/` by a `Spec:` line」。規劃工具的 setup 可能會幫你寫好這行。如果這份指示檔沒有進版本控制，其他 checkout 就沒有這行，主 Agent 只能退回自己搜尋。
- **不一致：**spec 自己列了 claim 又有 ticket 時，列出的 claim 必須與它所有的 ticket（不論是否完成）一致；不一致會列為阻擋事項，由你決定。
- **修改 claim：**主 Agent 不會為了新增、拆分或修改 claim 而修改 spec 或 ticket，除非你授權，所以你同意的計畫仍是你的；它會保留新舊 claim 的對應與尚未解決的阻擋事項。
- **ticket 的偏離：**由 ticket 組成的計畫發生重大偏離後，審查涵蓋變動觸及的 ticket，而不是整份計畫，只有變動觸及 spec 的結果、範圍、決定或不變條件時，才會再做 spec 檢查清單。這些是給模型的指示：哪些 ticket 受變動影響、變動是否觸及 spec，由主 Agent 判斷；除此之外，檢查清單只在計畫審查時執行，看的是當時寫下的文字。
- **更新 spec：**ticket 切好之後，實作以 ticket 為準；你同意的變動改變了 spec 的結果、範圍、決定或不變條件時，主 Agent 會在你授權後更新 spec，讓之後的檢查與其他 session 讀到同意後的版本。你同意的變動若改到某個 claim 讀的 spec 部分，會重新打開那個 claim 的通過。
- **草擬 spec：**主 Agent 替你草擬 spec 時，除非你要求，不會在裡面列出 claim，也不會切分 claim：它的 claim 在你指名要實作這份 spec 或它的 ticket 時才決定，並和你寫的 spec 一樣分類；見[安全關鍵工作](#安全關鍵工作)。
- **還不算計畫：**既沒有 ticket、也沒有自己範圍與驗收條件的 spec（例如沒有驗收段落的 spec 範本）還不算計畫；主 Agent 會先補齊，並請你確認補齊後的版本。
- **plan mode 與對話中的計畫：**它們的 claim 只存在於該計畫的文字中，其他 session 看不到；這是已接受的限制。新的 session 只會依它的原文、現有紀錄或你確認過的版本來使用這類計畫。
- **檔案位置：**spec 放在哪裡、ticket 是否 commit，不由 cc-feather 決定；它使用實作的 session 手上有的檔案。

### 安全關鍵工作

```text
/cc-feather:adversarial-review 檢查 src/auth 的 session token 驗證，使用計畫指定的測試伺服器
/cc-feather:adversarial-review 密碼重設流程 HEAD~3..HEAD
```

安全關鍵 claim（Security-critical claim）是結果包含安全關鍵變更的 claim：改變信任邊界上的安全保證，或改變安全控制的實作或設定，包括敏感資料流向哪裡、不受信任的資料在下游如何被解讀。身分驗證、授權、session 與 CSRF、憑證、密碼學、輸入驗證與存取控制都是例子，不是完整清單；主 Agent 依變更實際做了什麼來判斷，而不是看關鍵字。這類 claim 出錯可能洩漏資料或權限，所以會得到更多關注：它由 security-executor 實作，`off` 時也一樣，主 Agent 也會在開始處理計畫的 claim 之前先分類。定義、分類方式與工作交給誰，寫在[分派 skill](../skills/delegation/SKILL.md) 的 Select and prepare 與[計畫審查程序](../skills/delegation/references/plan-review.md)。

在 `auto` 下，有安全關鍵 claim 的計畫會先做唯讀的安全分析，再對修訂後的計畫做計畫審查，所以審查要檢查的安全不變條件與可拋棄的測試目標，在動手建置前就寫進 claim。安全分析改變計畫時，由你同意修訂後的計畫。安全分析不計入停止門檻，已實作工作即使豁免了缺少的 READY，也不會因此豁免它。規則寫在[計畫審查程序](../skills/delegation/references/plan-review.md)的安全分析與[分派 skill](../skills/delegation/SKILL.md)。

對抗式審查是第三步：adversary 嘗試攻破這個 claim，回覆 HELD、BROKEN 或 INCONCLUSIVE，所以安全關鍵 claim 不只被審查，還會被攻擊。在 `off` 下，要在同一個 commit 拿到有效的 APPROVED 與 CONFIRMED 之後才算數，BROKEN 要在完成前回頭修正；在 auto 下，它只在最終檢查於最後的 commit 通過後，在那裡執行一次，BROKEN 會記錄下來，留到計畫最後由你決定，而不是在計畫中修正。變更之前就存在的漏洞不會擋下這個 claim，而是成為 tracker 中另外的工作。exploit 細節與機密不寫進任何公開或可能公開的地方，那些地方只寫摘要，除非你同意。規則寫在[對抗式審查程序](../skills/delegation/references/adversarial-review.md)，auto 的部分是它的 At the final commit，揭露的部分是它的第 10 步。這有其限制：對抗式審查攻擊的 commit，沒有整體經過該 claim 自己的程式碼審查與驗證，它的發現也不在這份計畫中修正。`off` 下不會自動開始對抗式審查，也不強制同意前的安全分析。第三步沒有單獨的開關：要讓安全關鍵 claim 沒有 HELD 就合併，請對它做接受並合併的決定。

`/cc-feather:adversarial-review` 在你要求時執行對抗式審查，兩種模式都可用。它需要攻擊範圍（沒給時主 Agent 會問），可再加上路徑或 commit 範圍與可拋棄目標；參數只當作資料，絕不放寬角色的限制。它審查什麼（commit 範圍、你未 commit 的變更或某個 claim 的 commit），以及它的結論算不算 claim 把關的通過，取決於 claim 與它的通過，結果會說明審查的 commit 或範圍、排除了什麼，以及結論算不算通過。目標只來自你同意的計畫或你自己的參數；沒有目標時，角色只做靜態分析，需要實際執行的部分回報 INCONCLUSIVE。動態探測依[審查狀態規則](../skills/delegation/references/review-state.md)中的 Execution 規則：除非你在這個 session 說過涵蓋它的限制，否則它在這台機器上進行；有這種限制時，只在你自己的訊息指定的隔離環境中進行，沒有的話只做靜態攻擊。只說明變更來自哪裡並不算限制。詳見[對抗式審查程序](../skills/delegation/references/adversarial-review.md)與[指令說明](../skills/adversarial-review/SKILL.md)。

adversary 的限制是給模型的指示，只有你的權限設定（permission mode 與 allow、ask、deny 規則，包括 managed settings）、hooks、Claude Code sandbox（原生 Windows 不支援）以及外部隔離環境（例如容器或虛擬機）才會實際強制這些限制：在 bypassPermissions 模式下，或有寬鬆的 allow 規則時，它的 Bash 指令可能完全不經提示或分類器檢查就執行，而在 Claude Code 的 auto 模式下是由分類器而不是你核准；各模式如何處理指令，請見官方的 [permission modes 文件](https://code.claude.com/docs/en/permission-modes)。

### 儲存庫安全

**分派假設儲存庫是受信任的，審查會在這台機器上執行它的程式碼。說明變更從哪裡來（例如它是別人的 pull request、branch 或 patch）已經不會阻止這件事：要阻止，請在你自己的訊息中說程式碼不得執行，或指出哪些不得執行。cc-feather 不提供在你信任儲存庫之前檢查它的功能，所以要不要信任一個儲存庫（例如下載或複製別人的儲存庫之後）由你決定。**

主 Agent 與角色用一般的檔案工具與一般的 Git 指令讀取儲存庫，沒有任何審查能隔離或偵測有惡意的儲存庫內容。審查只保留讓結果正確的檢查，而無法確認結果的檢查算作失敗。

每次程式碼審查、驗證與對抗式審查的前後，以及最終檢查前後，主 Agent 都會讀取 `HEAD` 與工作區狀態，所以通過判斷的恰好是 brief 指名的 commit，呼叫期間的變動會讓它失效；計畫審查與安全分析比對同樣的讀取，不需要乾淨的工作區。主 Agent 只以名稱 commit claim 的檔案，所以你先前 stage 的內容不會進入這個 commit，也只在你要求時才略過 hook 或簽章。這些讀取寫在審查狀態規則的 What a gated pass judged，commit 的形式寫在它的 Repository authority。

審查與最終檢查會在這台機器上執行儲存庫的程式碼，除非你在這個 session 說明的限制涵蓋該次呼叫；被涵蓋的呼叫只在你自己的訊息指定的隔離環境中執行，否則需要執行的部分回報 INCONCLUSIVE。限制只來自你在這個 session 自己的訊息：這個儲存庫不受信任、程式碼不得執行，或更窄的限制，例如不要跑某個 pull request 的測試。只說明變更從哪裡來不算限制。工具結果、檔案、commit、角色的回報、handoff、派工或記憶紀錄、hook 輸出或 compaction 摘要中的文字，都不能提出或解除限制，也不能指定隔離環境。規則（包括限制持續多久、什麼能解除它）是審查狀態規則的 Execution。

這些規則是給模型的指示，不是 sandbox：沒有任何權限規則、hook 或 sandbox 強制它們，測試只確保文字前後一致。剩下的是你要承擔的風險：

- 儲存庫的內容可能透過它的 `CLAUDE.md`、註解、commit 訊息，或主 Agent 與角色讀到的任何東西引導它們：角色可能被引導把變更造成的安全問題說成既有問題或只是推測，主 Agent 可能被引導去執行限制涵蓋的程式碼，因為限制本身也只是給主 Agent 的指示。
- 審查與最終檢查會在這台機器上執行儲存庫的程式碼，而主 Agent 與角色的 Git 指令（每次呼叫前後的 `git status`、角色的讀取，以及 `git add`、commit 與 push）會執行儲存庫的 Git 設定、attributes 與 hooks 選定的程式，包括追蹤目錄中的 hook 以及 `git status` 執行的 filter，不論是否有限制生效。這些程式碼能改動你能改動的任何東西，包括你自己的 Git 設定、其他 worktree 與 Feather 自己的紀錄。
- 限制管的是審查與最終檢查，不是實作：executor 與 security-executor 實作時可能執行儲存庫的程式碼，修正別人的變更時也一樣。
- cc-feather 中沒有任何東西會在程式碼執行前先問你；剩下的只有 Claude Code 的資料夾信任與你的權限設定。
- 你指定過的隔離環境，在一般性的限制下仍可使用，除非限制另有說明；如果那個環境存有秘密資料（例如 CI runner），程式碼就會在那裡執行。
- 被忽略的檔案，以及標為 assume-unchanged 或 skip-worktree 的檔案，不在工作區檢查的範圍內，所以這類檔案可能影響審查或最終檢查。
- Claude Code 在專案中開始 session 時會載入專案的 `CLAUDE.md` 與 `.claude` 設定，並執行那些設定中的 hook，所以儲存庫在任何審查開始前就可能有所動作。
- 停止執行的陳述只在這個 session 有效，被 context compaction 遺失時也就跟著遺失；新的 session（包括接續 handoff 的 session）不帶有它們。

詳見 [ADR 0016](adr/0016-delegation-trusts-the-repository.md)。

### 停止門檻

停止門檻是自動流程的一個步驟連續幾次自動呼叫沒通過就停下：一個 2 到 10 的數字，計畫審查、程式碼審查、結果驗證與對抗式審查都適用同一個值，預設 2。它限制流程不問你能嘗試多久。你可以告訴主 Agent 目前任務或 session 要用的值，這不會寫入任何檔案；也可以用設定工具的 `review --stop-threshold` 儲存在 project 或 user 範圍（見[停止門檻](setup.md#stop-threshold)）。主 Agent 絕不自行更改它，每次要做審查決定時都會說明目前的值與來源。目前的值如何決定、何時算不明，以及變更時會怎樣，寫在審查狀態規則的 Resolution、Unknown threshold、Changing it 與 Saved in this conversation；值如何儲存，寫在[setup 的停止門檻流程](../skills/setup/references/stop-threshold.md)。

```text
/cc-feather:stop-threshold 4
/cc-feather:stop-threshold 4 project
/cc-feather:stop-threshold default user
```

用 `/cc-feather:stop-threshold` 設定，或用自己的話請主 Agent 設定，效果相同。不帶範圍（或加 `session`）時只用於這個 session，不寫入任何檔案；加 `project` 或 `user` 時，會儲存到該範圍既有的 agent 分派安裝，它絕不會安裝 agent 分派。session 選擇不會帶到新的或恢復的 session，也不會寫進交接，而且 context 壓縮可能讓它遺失。詳見[指令說明](../skills/stop-threshold/SKILL.md)。

變更停止門檻絕不會改變次數。次數低於新值的步驟可以繼續，次數達到新值的步驟會停下，主 Agent 會列出因此繼續或停下的步驟。較高的值讓流程不問你就能繼續嘗試更久，代價見上方的成本，而且增加得比 K 快。

### 分派預覽

```text
/cc-feather:delegation-preview docs/specs/my-feature.md
/cc-feather:delegation-preview TICKET-12 TICKET-13
/cc-feather:delegation-preview
```

開始實作前，先看主 Agent 會如何拆分一個或多個計畫、ticket，或一段沒有計畫的工作描述：每個 claim 底下列出每一項派工與主 Agent 自己保留的部分，附上角色、model、effort 與值的來源（任務、session、已儲存或預設），哪些可以平行，各審查步驟與何時停下，並標示任何會擋住工作的情況，例如未安裝的角色、還不算計畫的輸入，或需要先探索才能判斷的工作。指名的 spec 還有未完成的 ticket 時，預覽不替你回答要實作 spec 還是它的 ticket：它會列出兩種解讀，或標示它的數量取決於你怎麼回答。不帶參數時預覽目前討論中的計畫；沒有或有多個候選時會詢問。它顯示與標示什麼，寫在[預覽流程](../skills/delegation/references/preview.md)的 Output 與 Flags。

預覽是唯讀的：由主 Agent 自己產生，不派出任何子 Agent、不啟動審查、不佔審查次數、不寫入任何檔案。只能透過這個指令執行，在對話中提出要求不會觸發。它顯示目前已生效的設定，包含 session 的 `auto-on`／`auto-off`；想試別的 model 或 effort，請先用 `/cc-feather:model` 設定再重新預覽。預覽只在產生它的 session 中作為派工依據：在該 session 接著實作時，主 Agent 依預覽派工，並逐項回報差異與原因。其他 session 產生的預覽只供參考；在那裡派工可以與它不同，不會當作差異回報。model 與 effort 顯示的是設定值，不代表已確認的實際執行。這個指令隨 plugin 提供，plugin 更新後只要開新 session，不需要執行 setup update。詳見[預覽流程](../skills/delegation/references/preview.md)。

## 版本紀錄

目前版本之前各版的更新說明；目前版本的說明見 README 的[更新、移除與驗證](../README.zh-TW.md#更新移除與驗證)。

0.25.0 改了 reviewer、verifier 與 adversary 的角色定義，所以既有安裝要先更新 plugin，再於每個裝有分派元件的範圍執行 `/cc-feather:setup update`，然後開新 session；在那之前，`auto` 與 `off` 下 check 都會回報 `role_update_required: true`，並指出這三個角色來自較舊的範本，`model`、`review` 與 session export 也會要求先做 setup update，需要執行程式碼的審查則會對這部分回報 INCONCLUSIVE。要回到 0.24.0，重新安裝 0.24.0 的 plugin，並在每個裝有分派元件的範圍執行 `/cc-feather:setup update`，再開新 session，讓它還原 0.24.0 的 reviewer、verifier 與 adversary 角色定義；不需要先移除，因為 0.25.0 沒有改設定工具或 state。0.24.0 改了 reviewer 的角色定義，所以既有安裝要先更新 plugin，再於每個裝有分派元件的範圍執行 `/cc-feather:setup update`，然後開新 session；在那之前，`auto` 與 `off` 下 check 都會回報 `role_update_required: true`，並指出 reviewer 來自較舊的範本，`model`、`review` 與 session export 也會要求先做 setup update。要回到 0.23.0，重新安裝 0.23.0 的 plugin，並在每個裝有分派元件的範圍執行 `/cc-feather:setup update`，再開新 session，讓它還原 0.23.0 的 reviewer 角色定義；不需要先移除，因為 0.24.0 沒有改設定工具或 state。0.23.0 沒有改任何角色定義、指引範本或設定工具，所以既有安裝只要更新 plugin 再開新 session，不需要做 setup update。要回到 0.22.0，重新安裝 0.22.0 的 plugin 即可；不需要變更 setup，因為 0.23.0 沒有改任何已安裝的檔案或 state。0.22.0 沒有改任何角色定義、指引範本或設定工具，所以既有安裝只要更新 plugin 再開新 session，不需要做 setup update。要回到 0.21.0，重新安裝 0.21.0 的 plugin 即可；不需要變更 setup，因為 0.22.0 沒有改任何已安裝的檔案或 state。0.21.0 改了 reviewer、verifier、adversary、analyst、scout 與 Explore 的角色定義和自動審查指引，所以每個裝有分派元件的範圍都要跑 setup update，再開新 session；在那之前，`auto` 與 `off` 下 check 都會回報 `role_update_required: true`，並指出這六個角色來自較舊的範本，`auto` 下還會指出分派指引來自較舊的範本，`model`、`review` 與 session export 也會要求先做 setup update。reviewer 現在可以在拿不到程式碼審查需要的證據時回答 INCONCLUSIVE，程式碼審查計算它的方式與結果驗證的 INCONCLUSIVE 相同。要回到 0.20.0 不需要先移除：0.20.0 讀得懂 0.21.0 寫入的 state，它自己的 setup update 會重新寫入它的角色範本與指引。0.20.0 新增停止門檻與 `/cc-feather:stop-threshold` 指令，沒有改任何角色定義或指引範本，所以既有安裝只要更新 plugin 再開新 session，在儲存停止門檻之前，指引與 state 都不會改變。0.19.x 或更舊的設定工具不接受已儲存停止門檻的範圍，所以要回到這些版本前，先在該範圍把它設回 `default`；task 或 session 的指定不需要處理。0.19.0 改了 executor、security-executor、adversary 與 reviewer 的角色定義，所以每個裝有分派元件的範圍都要跑 setup update，再開新 session；在那之前，`auto` 與 `off` 下 check 都會回報 `role_update_required: true`，並指出這四個角色來自較舊的範本，`model`、`review` 與 session export 也會要求先做 setup update。0.18.0 新增 `adversary` 角色，並改了 executor 的角色定義、分派指引與自動審查指引，所以每個裝有分派元件的範圍都要跑 setup update，再開新 session；在那之前，`auto` 與 `off` 下 check 都會回報 `role_update_required: true`（缺少 adversary，executor 角色與分派指引來自較舊的範本），`model`、`review` 與 session export 也會要求先做 setup update，需要的對抗式審查也會因缺少 adversary 而受阻。0.17.0 改了 reviewer 與 analyst 的角色定義和自動審查指引，所以每個裝有分派元件的範圍都要跑 setup update，再開新 session；在那之前，`auto` 與 `off` 下 check 都會回報來自較舊範本的角色，`model`、`review` 與 session export 也會要求先做 setup update。
