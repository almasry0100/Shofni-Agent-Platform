# فكرة المستويين 2 و3

**User:** Anonymous  
**Created:** 9/29/2026 14:52:51  
**Updated:** 9/29/2026 15:38:01  
**Exported:** 9/29/2026 15:39:44  
**Link:** [https://chatgpt.com/c/6abba692-0390-83ea-b24e-927be0250a88](https://chatgpt.com/c/6abba692-0390-83ea-b24e-927be0250a88)  

## Prompt:
9/29/2026, 2:56:24 PM

اقرا نص الملف بالكامل سطر سطر وكلمة كلمة وافهمه الملف بالكامل وطلع ليه فكرة المستوي 2 و 3 بشكل دقيق ومنفصل

[Attachment: ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md]

## Response:
9/29/2026, 2:56:28 PM · gpt-5-6-thinking

هراجع الملف كامل من أول سطر لآخر سطر، مش بس الجزء الظاهر في المعاينة. وبعدها هفصل لك **فكرة Level 2** و**فكرة Level 3** كل واحدة كتصميم مستقل: الهدف، المعمارية، مسار التنفيذ، المسؤوليات، حدودها، وما الذي يميزها فعليًا عن الأخرى.

خلصت قراءة الملف كاملًا حتى آخر سطر. أهم نقطة خرجت بها إن الفكرة **اتطورت أثناء الشات**: Level 2 بدأ كـOpenCode Tool Bridge، ثم استقر في النهاية كـ**Multi-Client Shofni Agent Gateway**؛ وLevel 3 مش مجرد “Bridge أقوى”، بل **نقل ملكية الـAgent Loop والتنفيذ والحالة والسياسات بالكامل إلى Runtime خاص بنا**.

> **Reading and separating level 2 and level 3 ideas**
>
>
> **Analyzed documents in chunks and extracted structured ideas**
>
> 
>
> **Reading First 300 Lines**
>
>
> **Clarifying levels two and three**
>
> سأفصل بين المستوى الثاني، بوصفه طبقة توافق وبوابة للأدوات، والمستوى الثالث، بوصفه طبقة تنسيق وتشغيل ومراقبة. سألتزم بما يورده الملف دون إضافة افتراضات خارجية.
>
> **Clarified levels two and three**
>
> 
>
> **Read and extracted script lines 1 through 2006**
>
> 
>
> Worked for 1m 23s

قرأت الملف كاملًا من أوله لآخره، وبالذات كل المراحل التي تطورت فيها فكرة **Level 2** و **Level 3**. الفكرة النهائية في آخر الملف أدق من التعريف الأول، لأن التصميم اتوسع لاحقًا ليشمل OpenCode وCodex وClaude Code، واتضح أيضًا أن المشكلة الأساسية ليست أن الـShell أو الـfilesystem غير موجودين، وإنما أن **طبقة الـtool-calling والـagent loop بين الـclient والـprovider غير موثوقة**: أحيانًا Tool Call ينجح، ثم الموديل يتوقف أو يقول إنه سينفذ بدون أن يصدر Tool Call جديد. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

# Level 2 - Shofni Agent Gateway / Tool Compatibility Bridge

الفكرة الدقيقة لـLevel 2 هي أننا **لا نبني Agent جديدًا**. نترك OpenCode أو Codex أو Claude Code يقوم بدور الـAgent كما هو، ونضع بينه وبين RelayRouter/A6api/OpenRouter طبقة توافق ذكية.

المفهوم النهائي يصبح:

```text
OpenCode ───────┐
Codex ──────────┼──→ Shofni Agent Gateway ──→ RelayRouter
Claude Code ────┘                          ├─→ A6api
                                          ├─→ OpenRouter
                                          └─→ Other Providers
```

في التعريف الأصلي كان OpenCode هو العميل الأساسي، والـBridge يستقبل `messages + model + tools[] + tool_choice + stream`. لو الـprovider يدعم Native Tools بشكل صحيح، يمررها كما هي تقريبًا. ولو الـprovider Text-only أو يضيع الـtools، يحول الأدوات إلى Structured Instructions، ينتظر JSON Action من الموديل، ثم يحولها مرة أخرى إلى Native Tool Call يفهمها العميل. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

لكن أثناء الشات الفكرة تطورت من `shofni-opencode-bridge` إلى **`shofni-agent-gateway` متعدد العملاء**. وبالتالي لا نبني Bridge مخصوصًا لـOpenCode فقط؛ بل Gateway عنده Adapters لبروتوكولات مختلفة مثل `/v1/chat/completions` و`/v1/responses` و`/v1/messages`، وتتحول كلها داخليًا إلى Protocol موحد. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

## ماذا يملك Level 2 فعليًا؟

هو يملك **طبقة التوافق والترجمة**، وليس دورة حياة الـAgent.

مثلًا Codex قد يرسل Tool Schema بشكل معين، وClaude Code بشكل مختلف، وOpenCode بشكل ثالث. الـGateway يحول الثلاثة إلى شيء داخلي موحد:

```text
NormalizedTool
{
  name
  description
  inputSchema
}
```

ثم يترجمه إلى الصيغة المناسبة للـprovider. والعكس أيضًا: لو RelayRouter أرجع Tool Call بصيغة نصية أو JSON غير Native، الـGateway يحوله إلى الصيغة التي يتوقعها Codex/OpenCode/Claude Code. هذه كانت النقلة الأساسية التي جعلت Level 2 مستقلًا عن Client واحد. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

والـBridge نفسه **لا ينفذ Shell Commands**. هذه نقطة أساسية جدًا في تصميم Level 2. لو الموديل طلب:

```json
{
  "tool": "shell",
  "arguments": {
    "command": "git status"
  }
}
```

فالـGateway يحوله إلى Tool Call ويرجعه للعميل، وبعدها OpenCode/Codex/Claude Code هو الذي ينفذ على الـlocal workspace الحقيقي. هذا يقلل صلاحيات الـGateway ويحافظ على الـexecution model الموجود أصلًا. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

يعني مسار Level 2 النهائي تقريبًا:

```text
User
 ↓
Codex / Claude Code / OpenCode
 ↓
Shofni Agent Gateway
 ↓
Normalize request + tools
 ↓
Provider
 ↓
Native Tool Call?
 ├─ Yes → Normalize → Client
 └─ No  → Parse/Emulate structured action → Client
 ↓
Client executes tool locally
 ↓
Tool Result
 ↓
Gateway
 ↓
Provider
```

## والمشكلة الحالية التي يحلها؟

لو RelayRouter أو OpenRouter أسقط `tools[]`، نحن لا نحتاج أن نعتمد على الـnative function calling. يستطيع الـGateway أن يشرح الأدوات للموديل ويطلب منه Structured Output صارم:

```json
{
  "type": "tool_call",
  "name": "read_file",
  "arguments": {
    "path": "..."
  }
}
```

ثم يحوله إلى Tool Call فعلي. وحتى لو الموديل كتب `tool_call` كنص بدل Structured Event، يمكن للـGateway Parse الرد وإعادة بنائه. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

Level 2 يستطيع أيضًا إضافة طبقة Repair بسيطة. فإذا الموديل قال:

```text
"I will read the file now."
```

بدون Tool Call، يستطيع الـGateway اعتباره:

```text
INVALID_AGENT_ACTION
```

ثم يعيد الطلب بشروط مثل:

```text
Return either:
1. TOOL_CALL
2. FINAL

No narration-only responses.
```

وده يعالج جزءًا كبيرًا من مشكلة «سأنفذ» بدون تنفيذ. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

لكن هنا **الحد الأساسي لـLevel 2**:

```text
Codex / Claude Code / OpenCode
        =
      Agent
```

هم الذين ما زالوا يملكون Conversation State والـAgent Loop وقرار الاستمرار بعد Tool Result ومتى تنتهي المهمة. الـShofni Gateway ما زال Translator/Compatibility Layer في المنتصف. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

وده معناه أن Level 2 يصلح **Tool Compatibility** بدرجة كبيرة، لكنه لا يملك الـworkflow بالكامل.

---

# Level 3 - Shofni Local Agent Runtime

Level 3 فكرة مختلفة معماريًا، وليس مجرد Level 2 مع Features إضافية.

هنا نقول:

```text
OpenCode/Codex/Claude Code
لم يعودوا الـAgent الحقيقي.

Shofni Runtime
هو الـAgent.
```

والموديل نفسه يصبح مجرد **Brain/Reasoning Engine**.

التصميم الأساسي الموجود في الملف:

```text
Shofni Agent Runtime
        │
        ├── Model Router
        ├── Tool Executor
        ├── Workspace Manager
        ├── Policy Engine
        ├── State Machine
        ├── Audit / Evidence
        └── Recovery
```

وبالتالي RelayRouter أو GPT أو Claude أو Gemini أو A6api يصبح مجرد Model Backend يستقبل Context ويرجع قرارًا/Tool Request. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

المسار هنا يصبح:

```text
User
 ↓
Shofni Runtime
 ↓
Model
 ↓
TOOL_REQUEST
 ↓
Policy Engine
 ↓
Tool Executor
 ↓
Real Local Workspace
 ↓
Tool Result
 ↓
Shofni Runtime
 ↓
Model
 ↓
...
 ↓
FINAL
```

وهنا الفرق العملاق: **Shofni Runtime هو الذي يعيد Tool Result للموديل ويقرر هل المهمة انتهت أم لا.**

## القلب الحقيقي لـLevel 3: Agent Loop

في الملف الـAgent Loop موضح بالشكل التالي تقريبًا:

```text
while not finished:

    ask model

    if final_answer:
        stop

    if tool_call:
        validate
        authorize
        execute
        record result
        send result to model
```

وبالتالي يمكن تنفيذ عشرات Tool Calls المتتابعة دون الاعتماد على أن OpenCode أو provider نفسه يدير الحلقة بصورة صحيحة. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

وده يحل المشكلة التي ظهرت في الاختبارات بشكل أعمق جدًا.

الحالة الحالية كانت:

```text
Tool Call ✅
Tool Result ✅
Next Tool Call ❌
finish: stop
```

في Level 3 تصبح:

```text
Tool Call ✅
Tool Result ✅

Model:
"I will read the file now."

Runtime:
❌ INVALID RESPONSE

Task unfinished.
Return TOOL_REQUEST or FINAL.

 ↓
Retry / Repair
 ↓

Next Tool Call ✅
```

فالـRuntime **لا يعتبر مجرد انتهاء Response من الموديل انتهاءً للمهمة**. هو عنده State Machine يعرف أن المهمة لا تزال مفتوحة. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

وده في رأيي هو أهم فرق تقني بين المستويين.

## Model Router

Level 3 عنده Model Router حقيقي:

```text
relayrouter/gpt-...
a6api/claude-...
openai/...
other-provider/...
```

والـRuntime لا يهتم بالبروتوكول الخارجي؛ كل Provider له Adapter ويحول ناتجه إلى Internal Contract مثل:

```json
{
  "type": "tool_request",
  "tool": "read_file",
  "args": {}
}
```

`ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

وده يسمح بأن المهمة نفسها تبدأ مثلًا بموديل، ولو حصل Failure حقيقي يمكن للـRuntime استخدام Retry أو Fallback لموديل آخر، مع الاحتفاظ بنفس Task State.

## Tool Registry + Tool Executor

في Level 3 الأدوات تصبح ملك Shofni نفسه:

```text
read_file
write_file
edit_file
list_directory
shell
git_status
git_diff
git_commit
run_tests
search_code
```

ثم لاحقًا:

```text
GitHub
Supabase
Vercel
MCP
Browser
```

والـTool Executor هو الذي ينفذها محليًا داخل الـworkspace المحدد. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

وده فرق جوهري عن Level 2:

```text
Level 2
Client executes tools.

Level 3
Shofni Runtime executes tools.
```

## Workspace Manager

كل Task يصبح Entity رسميًا عند النظام وله:

```text
task_id
repo
base_branch
worktree
cwd
allowed_paths
```

وبالتالي يمكن ربط كل مهمة بـGit Worktree مستقل ومنع الـAgent من الخروج منه. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

مثلًا مهمة على Shofni يمكن ربطها بـ:

```text
repo: Shofni
branch: feat/foo
worktree: /.../worktrees/feat-foo
```

وأي محاولة للوصول لمسار غير مسموح تُرفض.

## Policy Engine

ودي من أهم أفكار Level 3.

السياسات لا تبقى مجرد Prompt نقول للموديل «لا تعمل كذا». بل تصبح **Code-enforced rules**:

```text
read_file             AUTO
edit feature branch   AUTO
npm test              AUTO

merge integration     MANUAL
main                  DENY
production            DENY
supabase prod         DENY
force push            DENY
secrets               DENY
```

حتى لو الموديل طلب:

```text
git push origin main --force
```

فالـRuntime نفسه يمنع التنفيذ:

```text
DENIED_BY_POLICY
```

`ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

وده مهم جدًا لأن الـLLM **يقترح الفعل**، لكنه لا يملك سلطة تنفيذه مباشرة.

## Durable State + Recovery

وهنا Level 3 يتحول من Coding Proxy إلى Agent Platform حقيقي.

في البداية يكفي SQLite يحتوي على:

```text
tasks
attempts
tool_calls
tool_results
checkpoints
approvals
events
```

لو Codex وقع، أو الـprovider فصل، أو الجهاز اتعمله Restart، نقدر نعمل:

```text
resume from checkpoint
```

بدل إعادة المهمة من البداية. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

وده يسمح بشيء غير موجود فعليًا في Level 2:

```text
Task #123
started using Codex
        ↓
Codex unavailable
        ↓
resume checkpoint
        ↓
Claude continues

Same:
task_id
worktree
branch
evidence
policy
```

وده بالضبط معنى أن **Shofni Runtime أصبح Source of Truth للمهمة** بدل Codex أو Claude أو OpenCode. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

## Audit / Evidence

كل Action يمكن تسجيله:

```text
tool
command_hash
cwd
started_at
exit_code
result_hash
```

مع تجنب تسجيل الأسرار. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

وده يسمح فيما بعد بمعرفة بدقة:

```text
مين طلب العملية؟
أي موديل؟
على أي Task؟
في أي Worktree؟
ما الأمر الذي نُفذ؟
هل نجح؟
ما الـcheckpoint الناتج؟
```

وده مهم جدًا لنظام Autonomous Development طويل المدى.

## OpenCode وCodex وClaude Code في Level 3

في Level 3 دول لا يلزم أن يختفوا.

لكن دورهم يتغير.

يمكن أن يصبحوا:

```text
UI
Client
Worker
MCP Consumer
```

بدل:

```text
The Agent Runtime
```

والتصميم الأنظف المقترح داخل الملف كان أن Shofni Runtime نفسه يقدم MCP interface، بحيث Codex وClaude Code يستطيعان الوصول إلى أدوات Shofni المشتركة، بدل كتابة Tool Implementation مختلفة لكل Client. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

بمعنى:

```text
                Shofni Tools
                     │
        ┌────────────┼────────────┐
        ↓            ↓            ↓
     OpenCode    Claude Code    Codex
```

لكن الـstate والسياسات والتنفيذ الحقيقي يظل تحت سيطرة Shofni Runtime.

---

# نقطة مهمة جدًا عن حدود الشركات

Level 3 لا يعني أننا نستطيع إزالة قيود OpenAI أو Anthropic أو أي Provider.

المعمارية الصحيحة في الملف هي:

```text
Provider / Model Policies
          ↓
Model Output
          ↓
Shofni Policy Engine
          ↓
Tool Authorization
          ↓
Execution
```

يعني Provider Policies تظل موجودة، وفوقها نضيف **قيودنا نحن**. فإذا رفض الموديل شيئًا بسبب قواعد مزوده، الـRuntime لا يجبره. وإذا وافق الموديل على Action نحن نمنعه، فالـPolicy Engine يمنعه. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

ولو في المستقبل أردنا استقلالًا أكبر على مستوى الـBrain نفسه، الملف اقترح إمكانية استخدام Open-weight/Self-hosted model، لكن مع إبقاء Policy Engine؛ لأن امتلاك الموديل لا يلغي احتمال الخطأ أو hallucination. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

# إذن الفرق في جملة واحدة

| | Level 2 | Level 3 |
|---|---|---|
| الفكرة | **نصلح الطريق بين الـAgent والموديل** | **نبني الـAgent نفسه** |
| الـAgent الحقيقي | OpenCode / Codex / Claude Code | Shofni Runtime |
| Model | Brain | Brain |
| Tool translation | Shofni Gateway | Shofni Runtime |
| Tool execution | Client | Shofni Runtime |
| Agent Loop | Client | Shofni Runtime |
| Task State | Client-dependent | Shofni-owned |
| Checkpoints/Resume | محدود | أساسي |
| Policies | محدودة | Code-enforced |
| Workspace isolation | يعتمد على Client | Runtime-owned |
| Multi-model fallback | محدود | Native concept |
| Audit | محدود | كامل |
| Text-only models | ممكن عبر emulation | ممكن بشكل أصلي في التصميم |
| الاعتماد على Native Tools | لا | لا |

والأهم أن الملف نفسه انتهى إلى أن **Level 2 لا ينبغي بناؤه كمشروع مؤقت نرميه**. التصميم النهائي الصحيح هو بناء `shofni-agent-gateway` بطريقة تجعل الـNormalized Protocol والـprovider/client adapters أساسًا نستعمله بعد ذلك داخل Level 3. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

بصياغة معمارية أدق جدًا:

```text
Level 2
=
Compatibility Plane

Level 3
=
Compatibility Plane
+
Agent Orchestration Plane
+
Execution Plane
+
State Plane
+
Policy Plane
+
Recovery/Audit Plane
```

فـ**Level 2 يحل مشكلة الاتصال والتوافق مع الأدوات**، بينما **Level 3 يجعلنا نمتلك بيئة الـAgent نفسها End-to-End**. ودي، بعد قراءة الملف كله، هي الفكرة النهائية الدقيقة للمستويين-not مجرد أن Level 3 «نسخة أكبر» من Level 2.

## Prompt:
9/29/2026, 3:05:58 PM

سؤال هل المستوين 

- قادرين علي تجميع اكتر من بروفيدر
- هل قادرين علي حل مشكلة البروفيدر اللي بيقدم الموديل كشات بس وادوات مش متاحة معاه
- هل لو البروفيدر بيقدم الموديل وقادر يعمل ادوات بس بيحصل اخطاء وتوقفات المتسوين بيحلهم
- هلي لو البروفيدر مش بيدعم مثلا كلود ديسكتوب او كودكس ديسك توب بسبب مثلا مفيش توفيرر ريسبون ماسدج المستوين قادرين علي حل المشكلة ديه

## Response:
9/29/2026, 3:06:11 PM · gpt-5-6-thinking

> **Comparing integration layers**
>
> I’m distinguishing client-side adaptation from runtime orchestration: L2 can normalize providers and emulate structured tool calls, while L3 additionally owns routing, retries, fallbacks, validation, and protocol translation. Both require sufficient model output and cannot invent missing semantics.
>
> **Compared integration layers**
>
> 
>
> Worked for 13s

أيوه، لكن بدرجات مختلفة جدًا بين **Level 2** و**Level 3**. والأربع حالات اللي ذكرتها هي تقريبًا الأسباب الأساسية لبناء النظام أصلًا.

| الحالة | Level 2 - Gateway/Bridge | Level 3 - Agent Runtime |
|---|---|---|
| تجميع أكثر من Provider | ✅ نعم | ✅ نعم، وأقوى |
| Provider Chat-only بدون Tools | ✅ نعم عبر Tool Emulation | ✅ نعم، ولا يحتاج Native Tools أصلًا |
| Provider عنده Tools لكن فيها توقفات/أخطاء | ⚠️ يعالج جزءًا كبيرًا | ✅ أقوى بكثير |
| Provider غير متوافق مع Responses/Messages الخاصة بالعميل | ✅ من أهم وظائفه | ✅ نعم عبر Client Adapters |

### 1. تجميع أكثر من Provider

**Level 2: نعم.**

الـGateway يكون عنده Adapters لـ:

```text
RelayRouter
A6api
OpenRouter
OpenAI-compatible providers
Anthropic-compatible providers
...
```

ويقدم للـClients واجهة موحدة:

```text
OpenCode ──────┐
Codex ─────────┤
Claude Code ───┤
               ↓
        Shofni Gateway
               ↓
      ┌────────┼────────┐
      ↓        ↓        ↓
   A6api    Relay    Provider X
```

وده بالفعل جزء من تطور الفكرة في الملف: بدل Bridge خاص بـOpenCode، الفكرة أصبحت **Gateway متعدد الـClients والـProviders**. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

أما **Level 3** فيعمل ذلك بشكل أعمق عن طريق:

```text
Model Router
```

مثلًا:

```text
model:
relayrouter/gpt-x
a6api/claude-x
openai/gpt-x
provider-x/gemini-x
```

والـRuntime لا يهتم بالبروتوكول الأصلي؛ كلهم يتحولون إلى Internal Contract موحد. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

والميزة الإضافية في Level 3 أنك لاحقًا تستطيع عمل routing:

```text
Coding → Provider A
Large-context → Provider B
Cheap task → Provider C
Fallback → Provider D
```

بدون أن يعرف الـClient أي شيء عن ذلك.

---

### 2. Provider يقدم الموديل Chat فقط ولا يوفر Tools

**نعم، المستويان يستطيعان حلها**، بشرط مهم جدًا: أن الموديل نفسه قادر على اتباع Structured Instructions بشكل معقول.

افترض أن الـProvider لا يدعم:

```text
tools[]
tool_choice
tool_calls
```

ويقدم فقط:

```text
messages → text
```

Level 2 يستطيع تحويل تعريف الأدوات إلى Prompt:

```text
Available tools:

read_file(path)
write_file(path, content)
shell(command)
search_code(query)
```

ثم يطلب من الموديل:

```json
{
  "type": "tool_call",
  "name": "read_file",
  "arguments": {
    "path": "package.json"
  }
}
```

بعدها الـGateway يحول هذا الـJSON إلى Tool Call Native يفهمه Codex/OpenCode/Claude client.

يعني:

```text
Chat-only Provider
        ↓
Structured JSON text
        ↓
Shofni Gateway
        ↓
Synthetic native tool_call
        ↓
Codex / OpenCode
        ↓
Local Tool
```

وده بالضبط الـTool Emulation الذي تمت مناقشته في الملف. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

وفي **Level 3** الموضوع أنظف أصلًا، لأننا لا نحتاج أن يعرف الـProvider مفهوم Native Tools.

يكفي أن يرجع:

```json
{
  "type": "tool_request",
  "tool": "shell",
  "args": {
    "command": "npm test"
  }
}
```

والـRuntime نفسه ينفذه.

```text
Model
 ↓
structured text
 ↓
Shofni Runtime
 ↓
Validate
 ↓
Policy
 ↓
Execute
 ↓
Tool result
 ↓
Model
```

ولذلك النص نفسه وصف Level 3 بأن الـProvider **لا يحتاج Native Tools أصلًا**. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

لكن لا يوجد سحر هنا. لو الموديل نفسه ضعيف جدًا ولا يستطيع إخراج JSON صالح، أو الـProvider يقص الردود أو يغيرها بشكل غير قابل للتنبؤ، سنحتاج repair/retry، وقد لا تصل الموثوقية لموديل يدعم Native Tool Calling أصلًا.

---

### 3. Provider يدعم Tools لكن تحصل أخطاء أو توقفات

هنا يوجد فرق كبير بين Level 2 وLevel 3.

لو المشكلة مثل التي ظهرت عندك:

```text
Tool call ✅
Tool executes ✅
Tool result ✅

ثم:

"I will read the next file."

لكن:
Tool call ❌
finish: stop
```

**Level 2 يمكنه تحسين هذا جدًا**.

مثلًا يكتشف أن المهمة لم تنتهِ لكن الموديل أرجع كلامًا فقط:

```text
INVALID_AGENT_ACTION
```

ثم يعمل Repair:

```text
You have not completed the task.

Return exactly one of:

TOOL_CALL
FINAL
```

ويعيد الطلب.

الملف ناقش هذا السيناريو حرفيًا تقريبًا. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

كذلك يستطيع Level 2 إصلاح:

```text
tool_call كنص
```

وتحويله إلى:

```text
real structured tool_call
```

ويستطيع Normalize اختلافات الـschema بين providers.

لكن Level 2 عنده سقف مهم:

```text
Codex / Claude / OpenCode
لا يزال هو Agent Loop.
```

فالـGateway يستطيع repair/retry/normalize، لكنه لا يملك كل lifecycle للمهمة. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

**Level 3 يحل النوع ده أقوى بكثير**.

لأن عندنا:

```text
while task_not_complete:

    model_response = ask_model()

    validate(model_response)

    if tool:
        authorize()
        execute()
        save_result()
        continue

    if valid_final:
        finish()
```

فالـRuntime لا يقول:

```text
HTTP response انتهى
=
Task انتهت
```

بل يعرف أن:

```text
task.status = running
```

وإذا الموديل قال:

```text
I'll continue now
```

بدون Tool Call:

```text
Invalid transition
→ retry
```

وممكن أيضًا:

```text
retry same model
→ retry different route
→ fallback model
→ resume checkpoint
```

وده سبب أن Level 3 يعالج مشكلة الـmulti-step stopping بصورة أقوى بكثير. الـAgent Loop والـcheckpoints جزء أصيل من التصميم. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md` `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

لكن حتى Level 3 لا يستطيع إصلاح **Provider outage حقيقي** أو Model ID غير موجود مثلًا. هو يستطيع فقط:

```text
detect
retry
fallback
resume later
```

بدل أن تنهار المهمة كلها.

---

### 4. Provider لا يدعم Codex/Claude بسبب اختلاف البروتوكول أو عدم وجود Responses/Messages

**دي تحديدًا واحدة من أقوى استخدامات Level 2.**

مثلًا عندنا Provider لا يوفر إلا:

```text
POST /v1/chat/completions
```

لكن Codex يحتاج شيئًا قريبًا من:

```text
POST /v1/responses
```

ممكن الـGateway يعمل:

```text
Codex
 ↓
POST /v1/responses
 ↓
Shofni Gateway
 ↓
convert
 ↓
POST /v1/chat/completions
 ↓
Provider
 ↓
convert response
 ↓
Responses-compatible output
 ↓
Codex
```

ونفس الفكرة لو Claude-side client يتوقع:

```text
/v1/messages
```

بينما الـProvider عنده OpenAI Chat فقط:

```text
Claude-compatible request
          ↓
      Gateway
          ↓
Normalized Protocol
          ↓
OpenAI-compatible request
          ↓
Provider
```

الفكرة الأصلية حددت بالفعل endpoints مثل:

```text
/v1/chat/completions
/v1/responses
/v1/messages
/v1/models
```

`ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

والتصميم الأحدث في الملف جعلها:

```text
Clients
   ↓
Client Adapters
   ↓
Shofni Gateway
   ↓
Normalized Protocol
   ↓
Provider Adapters
```

`ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

فلو المشكلة ببساطة:

```text
Provider has model ✅

but:

Responses API ❌
Anthropic Messages API ❌
Tool schema incompatible ❌
Streaming format incompatible ❌
```

فـ**Level 2 مصمم تحديدًا لإخفاء الاختلافات دي**.

وLevel 3 أيضًا يستطيع ذلك؛ بل Level 3 يحتفظ بنفس Client Adapters/Gateway layer ثم يضيف Runtime وراءها.

---

لكن فيه حد مهم جدًا لازم نفرقه.

لو Codex/Claude client يسمح لنا بـ:

```text
custom base_url
أو
MCP
أو
custom provider
```

فالحل ممتاز.

أما لو التطبيق نفسه Hard-coded بحيث يقول مثلًا:

```text
أنا لا أقبل إلا api.vendor.com
```

ولا يسمح custom endpoint ولا MCP ولا أي integration، فالـGateway وحده لا يستطيع إجبار التطبيق على الاتصال به.

يعني المشكلة يجب أن تكون:

```text
Protocol incompatibility
```

وليس:

```text
Client intentionally prohibits third-party providers.
```

---

فلو لخصنا الأربع حالات بتاعتك:

```text
                    Level 2       Level 3

Multi Provider         ✅             ✅✅

Chat-only Model        ✅             ✅✅
No Native Tools

Broken Tool Calls      ✅/⚠️           ✅✅
Premature Stops

Missing Responses      ✅✅            ✅✅
/ Messages Protocol

Provider fallback      ⚠️             ✅✅

Task Recovery          ⚠️             ✅✅

Own Agent Loop         ❌             ✅
```

وأنا شايف إن في مشروعك **Level 2 هو الحل لمشكلة الـcompatibility، بينما Level 3 هو الحل لمشكلة الـreliability والاستقلال عن الـagent implementation بتاع أي شركة**.

والأفضل معماريًا فعلًا ألا نبنيهما كمشروعين منفصلين:

```text
Shofni Agent Platform

Layer 1
Client Adapters
├─ OpenCode
├─ Codex
└─ Claude

Layer 2
Protocol Normalization
├─ Chat Completions
├─ Responses
└─ Anthropic Messages

Layer 3
Provider Router
├─ RelayRouter
├─ A6api
├─ OpenRouter
└─ Others

────────────
ده Level 2
────────────

ثم نضيف:

Layer 4
Agent Loop

Layer 5
Tool Executor

Layer 6
Policy Engine

Layer 7
Task State / Checkpoints

Layer 8
Recovery / Fallback / Audit

────────────
وده يحوله Level 3
────────────
```

وبالتالي **كل شغل Level 2 تقريبًا يظل موجودًا ويصبح أساس Level 3، وليس شغلًا سنرميه لاحقًا**.

## Prompt:
9/29/2026, 3:09:35 PM

يعني قصدك نعمل مستوي 2 بعد كده نحوله ل3

## Response:
9/29/2026, 3:09:40 PM · gpt-5-6-thinking

بالضبط. **الأفضل نبني Level 2 من البداية بطريقة Modular، وبعدها نوسعه تدريجيًا إلى Level 3 بدل ما نبني مشروعين منفصلين.**

يعني البداية تكون:

```text
Level 2
Client Adapters
+ Protocol Normalization
+ Provider Adapters
+ Tool Emulation
+ Streaming/Retry
+ Multi-provider Routing
```

وده يحل لك فورًا مشاكل التوافق الحالية مع RelayRouter/A6api/OpenRouter، وChat-only models، واختلاف `/responses` و`/messages` و`/chat/completions`.

بعد ما يثبت نفسه، ما نرميش أي حاجة. نضيف فوقه:

```text
Agent Loop
+ Tool Executor
+ Workspace Manager
+ Policy Engine
+ Durable Task State
+ Checkpoints / Resume
+ Fallback / Recovery
+ Audit / Evidence
```

وساعتها نفس المشروع يتحول إلى **Level 3 Runtime**.

فالمسار الصح هو:

```text
Shofni Agent Gateway
        ↓
      Level 2
        ↓
يشتغل فعليًا ونختبره
        ↓
نضيف Agent Runtime layers
        ↓
      Level 3
```

المهم فقط ألا نبني Level 2 كـhack مخصوص لـOpenCode. نبنيه من البداية كـ**core platform** يدعم Codex + Claude Code + OpenCode + عدة Providers، عشان كل شغله يبقى قابل لإعادة الاستخدام في Level 3.

وفي رأيي ده أوفر وأأمن وأسرع طريق، بدل ما نقفز مباشرة لـLevel 3 ونحاول نبني Agent Runtime كامل قبل ما نثبت إن طبقة البروتوكولات والـproviders نفسها مستقرة.

## Prompt:
9/29/2026, 3:12:11 PM

طب انا مثلا مش عايز احط اي قيود علي التنفيذ ويبقي بصلاحيات كاملة ومفتوحه بحسب كل موديل مقدم من الشكة يعني القيود الوحيدة للموديل والتنفيذ هي قيوده اللي نازل بيها من الشركة او قيود برامج التشغيل نفسها زي كودكس ديسكتوب فمش عايز ازود قيود اصلا

## Response:
9/29/2026, 3:12:23 PM · gpt-5-6-thinking

أيوه، وده يغيّر تصميم **Level 3** شوية عن النسخة اللي كانت متصورة في الملف، لكن من غير ما يكسر الفكرة الأساسية.

أنت عايز المبدأ يكون:

```text
Shofni Runtime
لا يفرض قيود إضافية.

الموديل يملك كل ما تسمح به:
1. الشركة المقدمة للموديل
2. برنامج التشغيل نفسه
3. نظام التشغيل والحساب المحلي
4. صلاحيات الـAPIs والخدمات المتصلة
```

يعني مثلًا لو GPT عبر مزوده مسموح له يطلب عملية معينة، وCodex Desktop أو الـRuntime عنده صلاحية تنفيذها، **Shofni لا يتدخل ويمنعها**.

وده ممكن تمامًا.

### في Level 2

Level 2 أصلًا مناسب جدًا للفلسفة دي، لأنه مجرد:

```text
Client
↓
Compatibility / Translation Gateway
↓
Provider
```

فلو Codex Desktop عنده:

```text
Read      ✅
Write     ✅
Shell     ✅
Git       ✅
Network   ✅
MCP       ✅
```

الـGateway **لا يضيف Permissions خاصة به**.

هو فقط:

```text
translate
normalize
repair
route
emulate tools
```

ثم Codex نفسه ينفذ بما تسمح به صلاحياته الأصلية.

يعني:

```text
Provider restrictions
        +
Codex Desktop restrictions
        +
OS permissions
        =
Final permissions
```

لا توجد:

```text
Shofni restrictions
```

إضافية.

---

## وفي Level 3 نعمل نفس الشيء

في التصميم الموجود في الملف كان عندنا:

```text
Model
 ↓
Shofni Policy Engine
 ↓
Tool Executor
```

والـPolicy Engine كان ممكن يمنع أشياء مثل `main` أو Production أو Force Push. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

لكن ده **اختيار معماري وليس شرطًا لعمل Level 3**.

نقدر نغيره إلى:

```text
Model
 ↓
Tool Request
 ↓
Schema Validation
 ↓
Tool Executor
 ↓
Real System
```

أو حتى:

```text
Model
 ↓
Shofni Runtime
 ↓
FULL ACCESS Executor
 ↓
Machine / APIs
```

ويكون Authorization Mode:

```text
ALLOW_ALL
```

---

### الفرق المهم: Validation مش Permission

حتى لو عايز Full Access، أنا ما أشيلش **Schema Validation**.

لأن دي مش قيود صلاحيات.

مثلاً لو الموديل رجع:

```json
{
  "tool": "shell",
  "args": null
}
```

أو JSON مكسور، لازم الـRuntime يعرف إن الرد malformed.

لكن لو رجع بشكل صحيح:

```json
{
  "tool": "shell",
  "args": {
    "command": "some-command"
  }
}
```

ننفذه كما هو، طالما نظام التشغيل نفسه يسمح به.

يعني:

```text
Schema validation ✅
Safety policy      ❌
Action allowlist   ❌
Branch restrictions ❌
Production restrictions ❌
Command filtering ❌
```

بالشكل اللي أنت طالبه.

---

## وحتى Approval Gates ممكن نشيلها

بدل:

```text
read       AUTO
write      AUTO
shell      ASK
git push   ASK
production DENY
```

تبقى:

```text
read        AUTO
write       AUTO
edit        AUTO
shell       AUTO
git         AUTO
network     AUTO
MCP         AUTO
GitHub      AUTO
Supabase    AUTO
Vercel      AUTO
```

أي Tool متاح للـRuntime:

```text
AUTO
```

ولا يوجد Manual Gate من Shofni Runtime.

---

## لكن تظل فيه قيود لن نقدر نزيلها من عندنا

وده يتوافق مع النقطة التي ناقشناها في الملف: Level 3 لا يستطيع إلغاء Provider-level policies. `ChatGPT-تحليل الشات وخطة التنفيذ-20260929-1254.md`

التسلسل يصبح:

```text
        MODEL COMPANY
   GPT / Claude / Gemini / ...
            │
     provider policies
            ↓
          Model
            │
            ↓
      Shofni Runtime
     no added policies
            │
            ↓
       Tool Executor
            │
            ↓
     Operating System
            │
            ↓
External services/APIs
```

فمثلًا لو Claude نفسه رفض طلبًا:

```text
Claude restriction
→ Runtime لا يزيلها
```

ولو Codex Desktop عنده Sandbox:

```text
Codex restriction
→ Gateway لا يزيلها
```

ولو Windows user مش Administrator:

```text
OS restriction
→ Runtime لا يتجاوزها تلقائيًا
```

ولو GitHub Token لا يملك Admin Scope:

```text
GitHub restriction
→ Runtime لا يستطيع تنفيذ Admin action
```

لكن **إحنا لا نضيف فوقهم Layer رابعة من المنع**.

---

## وفي Level 3 الكامل عندنا طريقتان

لو Shofni Runtime نفسه هو Tool Executor:

```text
Model
 ↓
Shofni Runtime
 ↓
shell / filesystem / git / browser / MCP
 ↓
Your machine
```

فالـRuntime يعمل بنفس صلاحيات الـOS process الذي شغلته به.

لو شغلته User عادي:

```text
User permissions
```

لو شغلته Elevated/Admin:

```text
Admin permissions
```

ولو شغلته داخل WSL:

```text
WSL user permissions
```

يعني الـRuntime نفسه لن يخترع Sandbox إضافي.

---

## ومع Codex / Claude Code

ممكن أيضًا يكون الوضع:

```text
Model Provider
     ↓
Shofni Gateway
     ↓
Codex Desktop
     ↓
Codex own execution environment
```

هنا Codex هو من يحدد حدود التنفيذ.

أو في Level 3:

```text
Codex
  ↓
Shofni Runtime
  ↓
Local Executor
```

وساعتها صلاحية الـRuntime هي التي تحدد التنفيذ على الجهاز.

---

## وبالتالي أنا هعدل التصميم النهائي عندنا بالشكل ده

بدل:

```text
Policy Engine
├─ Allow
├─ Deny
├─ Ask
└─ Approval Gate
```

نخليه Component اختياري:

```text
Authorization Layer

mode:
  passthrough
```

أو:

```text
authorization:
  mode: unrestricted
```

بحيث النظام نفسه يدعم مستقبلًا:

```text
unrestricted
controlled
enterprise-policy
```

لكن إعدادك أنت يكون:

```text
unrestricted
```

وما يحصلش Block لأي عملية بسبب Shofni.

---

واللي أنصح نحتفظ به حتى في وضع **Full Access** هو فقط:

```text
Logging
Audit trail
Task state
Checkpoints
Tool result capture
Error recovery
Provider fallback
```

لأن الحاجات دي **لا تمنع الموديل من فعل أي شيء**.

هي فقط تخليك تعرف:

```text
what happened
which model did it
which command ran
what changed
whether it succeeded
```

وده مهم جدًا خصوصًا مع Agent ممكن يعمل عشرات أو مئات العمليات تلقائيًا.

فالتصميم النهائي المناسب لفكرتك يبقى:

```text
Models / Providers
        ↓
Shofni Gateway
        ↓
Protocol normalization
        ↓
Agent Runtime
        ↓
Agent Loop
        ↓
Tool Executor
        ↓
FULL ACCESS
        ↓
OS / Git / Files / MCP / GitHub /
Supabase / Vercel / Browser / APIs
```

**من غير Shofni Safety/Permission Layer إضافية.**

وبالتالي الحرية النهائية للموديل = **أقصى ما يسمح به الموديل نفسه + البرنامج الذي يشغله + الصلاحيات الفعلية للحساب والـAPIs**، وليس قيودًا نضيفها نحن.

## Prompt:
9/29/2026, 3:16:04 PM

تمام عايزين نحول فكرة المستوي التاني ل نظام قابل للتطوير وتحويله لمستوي 3

# Level 2 — Shofni Agent Gateway / Tool Compatibility Bridge

الفكرة الدقيقة لـLevel 2 هي أننا **لا نبني Agent جديدًا**. نترك OpenCode أو Codex أو Claude Code يقوم بدور الـAgent كما هو، ونضع بينه وبين RelayRouter/A6api/OpenRouter طبقة توافق ذكية.

المفهوم النهائي يصبح:

```
```

```
OpenCode ───────┐
Codex ──────────┼──→ Shofni Agent Gateway ──→ RelayRouter
Claude Code ────┘                          ├─→ A6api
                                          ├─→ OpenRouter
                                          └─→ Other Providers
```

في التعريف الأصلي كان OpenCode هو العميل الأساسي، والـBridge يستقبل `messages + model + tools[] + tool_choice + stream`. لو الـprovider يدعم Native Tools بشكل صحيح، يمررها كما هي تقريبًا. ولو الـprovider Text-only أو يضيع الـtools، يحول الأدوات إلى Structured Instructions، ينتظر JSON Action من الموديل، ثم يحولها مرة أخرى إلى Native Tool Call يفهمها العميل. 

لكن أثناء الشات الفكرة تطورت من `shofni-opencode-bridge` إلى **`shofni-agent-gateway` متعدد العملاء**. وبالتالي لا نبني Bridge مخصوصًا لـOpenCode فقط؛ بل Gateway عنده Adapters لبروتوكولات مختلفة مثل `/v1/chat/completions` و`/v1/responses` و`/v1/messages`، وتتحول كلها داخليًا إلى Protocol موحد. 

## ماذا يملك Level 2 فعليًا؟

هو يملك **طبقة التوافق والترجمة**، وليس دورة حياة الـAgent.

مثلًا Codex قد يرسل Tool Schema بشكل معين، وClaude Code بشكل مختلف، وOpenCode بشكل ثالث. الـGateway يحول الثلاثة إلى شيء داخلي موحد:

```
```

```
NormalizedTool
{
  name
  description
  inputSchema
}
```

ثم يترجمه إلى الصيغة المناسبة للـprovider. والعكس أيضًا: لو RelayRouter أرجع Tool Call بصيغة نصية أو JSON غير Native، الـGateway يحوله إلى الصيغة التي يتوقعها Codex/OpenCode/Claude Code. هذه كانت النقلة الأساسية التي جعلت Level 2 مستقلًا عن Client واحد. 

والـBridge نفسه **لا ينفذ Shell Commands**. هذه نقطة أساسية جدًا في تصميم Level 2. لو الموديل طلب:

```
```

```
{
  "tool": "shell",
  "arguments": {
    "command": "git status"
  }
}
```

فالـGateway يحوله إلى Tool Call ويرجعه للعميل، وبعدها OpenCode/Codex/Claude Code هو الذي ينفذ على الـlocal workspace الحقيقي. هذا يقلل صلاحيات الـGateway ويحافظ على الـexecution model الموجود أصلًا. 

يعني مسار Level 2 النهائي تقريبًا:

```
```

```
User
 ↓
Codex / Claude Code / OpenCode
 ↓
Shofni Agent Gateway
 ↓
Normalize request + tools
 ↓
Provider
 ↓
Native Tool Call?
 ├─ Yes → Normalize → Client
 └─ No  → Parse/Emulate structured action → Client
 ↓
Client executes tool locally
 ↓
Tool Result
 ↓
Gateway
 ↓
Provider
```

## والمشكلة الحالية التي يحلها؟

لو RelayRouter أو OpenRouter أسقط `tools[]`، نحن لا نحتاج أن نعتمد على الـnative function calling. يستطيع الـGateway أن يشرح الأدوات للموديل ويطلب منه Structured Output صارم:

```
```

```
{
  "type": "tool_call",
  "name": "read_file",
  "arguments": {
    "path": "..."
  }
}
```

ثم يحوله إلى Tool Call فعلي. وحتى لو الموديل كتب `tool_call` كنص بدل Structured Event، يمكن للـGateway Parse الرد وإعادة بنائه. 

Level 2 يستطيع أيضًا إضافة طبقة Repair بسيطة. فإذا الموديل قال:

```
```

```
"I will read the file now."
```

بدون Tool Call، يستطيع الـGateway اعتباره:

```
```

```
INVALID_AGENT_ACTION
```

ثم يعيد الطلب بشروط مثل:

```
```

```
Return either:
1. TOOL_CALL
2. FINAL

No narration-only responses.
```

وده يعالج جزءًا كبيرًا من مشكلة «سأنفذ» بدون تنفيذ. 

لكن هنا **الحد الأساسي لـLevel 2**:

```
```

```
Codex / Claude Code / OpenCode
        =
      Agent
```

هم الذين ما زالوا يملكون Conversation State والـAgent Loop وقرار الاستمرار بعد Tool Result ومتى تنتهي المهمة. الـShofni Gateway ما زال Translator/Compatibility Layer في المنتصف. 

وده معناه أن Level 2 يصلح **Tool Compatibility** بدرجة كبيرة، لكنه لا يملك الـworkflow بالكامل.

## Response:
9/29/2026, 3:16:22 PM · gpt-5-6-thinking

أيوه، وعلشان ما نرميش Level 2 بعدين، هنصممه من البداية كـ**نواة منصة** مش كـproxy سريع. الفاصل المهم هيكون: كل ما يخص **clients/providers/protocols/tools normalization** يبقى Core ثابت، وكل ما يخص **agent loop/execution/state/recovery** يبقى Layers نضيفها لاحقًا لتحويله لـLevel 3.

> **Designing evolution path**
>
> I’m shaping Level 2 as a stable runtime core, not a temporary prototype. I’m separating transport, provider adapters, canonical messaging, tool execution, repair, and observability so Level 3 can add planning without rewrites.
> 
> **Defining boundaries**
> 
> My central rule is one internal contract for messages, streams, tools, errors, and capabilities. Client formats terminate at the gateway; provider-specific schemas remain inside adapters. This prevents protocol drift and simplifies testing.
> 
> **Planning Level 3**
> 
> I’m reserving extension points for agent state, planning, workspaces, persistence, retries, branching, and human approval. Authorization stays optional and injectable rather than becoming a mandatory limitation, preserving the requested unrestricted default.
> 
> **Organizing implementation**
> 
> I’d structure a monorepo around `protocol`, `gateway`, `providers`, `tools`, `repair`, `observability`, `runtime`, and `tests`. Level 2 ships first; Level 3 composes these modules instead of replacing them.
> 
> **Protecting reliability**
> 
> I’m treating streaming and tool calls as stateful protocols with correlation IDs, replay-safe events, deadlines, cancellation, and consistent error envelopes. The repair layer should be bounded, observable, and never silently mutate user intent.
> 
> **Choosing persistence**
> 
> Level 2 can remain mostly stateless, with optional event logging. Level 3 can introduce durable sessions, checkpoints, artifact storage, and resumable execution behind interfaces, keeping storage choices independent from orchestration.
> 
> **Validating incrementally**
> 
> I’m recommending contract tests, adapter conformance tests, streaming simulations, malformed-input tests, timeout tests, cancellation tests, and failure-injection scenarios. This gives each provider and future agent runtime the same reliability baseline.
> 
> **Sequencing delivery**
> 
> I’d deliver canonical protocol and gateway first, then adapters, tools, repair, and observability. After those contracts stabilize, Level 3 adds planner, memory, workspace, and execution-state modules as separate capabilities.
>
> **Designed an evolution path**
>
> 
>
> **Designing the upgrade path**
>
> I’m defining Level 2 as a reusable compatibility runtime with two modes: passthrough for current clients and managed execution for Level 3. Both share the same normalized protocol, adapters, routing, tools, streaming, repair, observability, and tests. Level 3 adds orchestration, durable state, planning, workspaces, retries, and resumable execution above this stable core.
>
> **Designed the upgrade path**
>
> 
>
> Worked for 57s

بالضبط. هنحوّل Level 2 من مجرد **Bridge** إلى **Platform Core** مصمم من أول يوم بحيث Level 3 يكون إضافة Layers فوقه، وليس إعادة كتابة.

الاسم الأنسب للمشروع عندي:

**Shofni Agent Platform**

ويكون **`Shofni Agent Gateway` هو أول Runtime Mode فيه، أي Level 2**.

---

# 1. المعمارية التي أقترحها

بدل ما نبني:

```text
OpenCode Bridge
```

نبني:

```text
                    Shofni Agent Platform
                           │
          ┌────────────────┴────────────────┐
          │                                 │
     Client Layer                     Provider Layer
          │                                 │
 ┌────────┼────────┐               ┌────────┼─────────┐
 ↓        ↓        ↓               ↓        ↓         ↓
Codex   Claude   OpenCode        Relay     A6api   OpenRouter
          │                                 │
          └───────────┐       ┌─────────────┘
                      ↓       ↓
                 Canonical Protocol
                       │
                 Gateway Engine
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
     Routing      Tool Compat      Repair
        │              │              │
        └──────────────┼──────────────┘
                       ↓
                 Streaming Engine
```

في البداية ده كله يعمل كـLevel 2.

لاحقًا نضيف:

```text
                       │
                 Agent Runtime
                       │
          ┌────────────┼─────────────┐
          ↓            ↓             ↓
      Agent Loop   Tool Executor   State
          │            │             │
          ├──────── Workspace        │
          ├──────── Recovery ────────┤
          └──────── Evidence ────────┘
```

وساعتها أصبح Level 3.

---

# 2. أهم قرار معماري

ممنوع تمامًا أن يتكلم:

```text
Codex Adapter
```

مباشرة مع:

```text
RelayRouter Adapter
```

ولا:

```text
Claude Adapter
```

يعرف أي شيء عن A6api.

كل شيء في المنتصف يتحول إلى **Shofni Canonical Protocol**.

يعني:

```text
Codex
 ↓
Codex Adapter
 ↓
Canonical Request
 ↓
Provider Router
 ↓
RelayRouter Adapter
 ↓
RelayRouter
```

والعكس:

```text
RelayRouter response
 ↓
RelayRouter Adapter
 ↓
Canonical Response
 ↓
Codex Adapter
 ↓
Codex
```

ودي أهم حاجة ستمنع إعادة كتابة المشروع عند Level 3.

---

# 3. الـCanonical Protocol

نعمل Contract داخلي خاص بنا.

مثلًا الرسالة داخليًا:

```text
NormalizedMessage
{
    role
    content[]
}
```

والـTool:

```text
NormalizedTool
{
    name
    description
    inputSchema
}
```

والـTool Call:

```text
NormalizedToolCall
{
    id
    name
    arguments
}
```

والـTool Result:

```text
NormalizedToolResult
{
    callId
    output
    isError
}
```

والطلب الأساسي:

```text
NormalizedModelRequest
{
    model
    messages
    tools
    toolChoice
    stream
    metadata
}
```

والرد:

```text
NormalizedModelResponse
{
    output
    toolCalls
    finishReason
    usage
}
```

المهم إن ولا OpenAI Responses ولا Anthropic Messages ولا Chat Completions يبقوا الـinternal representation.

**Shofni Protocol هو Source of Truth.**

---

# 4. Client Adapters

يبقى عندنا Layer مستقلة:

```text
packages/client-adapters/

├── openai-chat
├── openai-responses
├── anthropic-messages
└── future-clients
```

وفي البداية تعرض Gateway endpoints مثل:

```text
/v1/chat/completions
/v1/responses
/v1/messages
/v1/models
```

وبالتالي لو Client يتكلم Responses:

```text
Responses
↓
Canonical
```

ولو Client آخر يتكلم Messages:

```text
Anthropic Messages
↓
Canonical
```

كل الباقي في النظام لا يعرف أصل الطلب.

---

# 5. Provider Adapters

نفس الفكرة في الاتجاه الثاني:

```text
packages/provider-adapters/

├── relayrouter
├── a6api
├── openrouter
├── openai-compatible
├── anthropic-compatible
└── future-provider
```

كل Provider Adapter مسؤول فقط عن:

```text
Canonical Request
     ↕
Provider Protocol
```

وبالتالي إضافة Provider جديد بعدين لا تحتاج تعديل Codex أو Claude adapters.

---

# 6. Capability Registry

دي إضافة مهمة جدًا لم تكن واضحة بالشكل الكافي في التصميم القديم.

كل Provider/Model يبقى عنده Capability Profile.

مثلًا:

```text
Provider: RelayRouter
Model: X

chat_completions       ✅
responses              ❌
anthropic_messages     ❌

native_tools           ❌
structured_json        ✅
streaming              ✅
parallel_tools         ❌

tool_result_continuation ⚠️
```

وموديل آخر:

```text
native_tools           ✅
tool_result_continuation ✅
responses              ✅
streaming              ✅
```

وبالتالي Gateway لا يعتمد على التخمين.

هو يعرف:

```text
هذا الموديل:
Native Tools موجودة
→ Passthrough

هذا:
Native Tools غير موجودة
→ Tool Emulation
```

---

# 7. Tool Compatibility Engine

ده قلب Level 2.

يتعامل مع ثلاث حالات.

### الحالة A — Native Tools سليمة

```text
Client tools
↓
Normalize
↓
Provider tools
↓
Native tool_call
↓
Normalize
↓
Client tool_call
```

أقل تدخل ممكن.

---

### الحالة B — Provider Chat-only

هنا:

```text
Native Tools ❌
Structured text ✅
```

نحوّل:

```text
tools[]
```

إلى Tool Contract داخل الـprompt.

والموديل يرجع:

```json
{
  "type": "tool_call",
  "name": "read_file",
  "arguments": {
    "path": "package.json"
  }
}
```

ثم:

```text
Text JSON
↓
Tool Emulator
↓
NormalizedToolCall
↓
Client Adapter
↓
Native tool call
```

وبالتالي موديل Chat-only يصبح عمليًا قادرًا على استخدام أدوات Client.

---

# 8. Tool Call Parser

لازم ما نعتمدش فقط على JSON المثالي.

نعمل parsing pipeline:

```text
Response
  │
  ├─ Native tool event?
  │        ↓
  │      accept
  │
  ├─ Canonical JSON?
  │        ↓
  │      parse
  │
  ├─ fenced tool_call block?
  │        ↓
  │      extract
  │
  ├─ recoverable malformed JSON?
  │        ↓
  │      repair
  │
  └─ normal final response
```

ده تحديدًا يساعد في المشكلة اللي ظهرت عندك لما `tool_call` كان يطلع كنص بدل Structured Event.

---

# 9. Repair Engine

لكن هنا لازم نصحح نقطة مهمة في التصميم القديم.

Level 2 **مش دايمًا يقدر يعرف إن المهمة لم تنتهِ**.

لأن الـAgent الحقيقي ما زال:

```text
Codex
Claude Code
OpenCode
```

فلو الموديل رجع:

```text
I'll read the file now.
```

Level 2 لا يملك دائمًا Task State كافي يقول إن دي إجابة غير نهائية.

لذلك Repair Engine في Level 2 يعمل بشكل موثوق عندما نكون في **Tool Emulation Contract**.

مثلًا نفرض:

```text
Every response must be exactly one of:

TOOL_CALL
FINAL
```

ساعتها:

```text
"I will read..."
```

=

```text
INVALID_PROTOCOL_OUTPUT
```

ونعيد المحاولة.

لكن معرفة:

> المهمة كلها لسه ما خلصتش.

دي فعليًا مسؤولية Level 3.

ودي نقطة مهمة جدًا في الفصل بين المستويين.

---

# 10. Streaming Engine

لازم نفصله أيضًا عن Provider Adapters.

لأن عندك:

```text
OpenAI SSE
Anthropic SSE
Responses events
Provider-specific streams
```

نحول كلهم إلى:

```text
CanonicalStreamEvent
```

مثلًا:

```text
response.started
text.delta
tool_call.started
tool_call.arguments.delta
tool_call.completed
usage
response.completed
error
```

وبعدها Client Adapter يعيد Encoding للـclient المطلوب.

ده هيوفر علينا مشاكل كبيرة جدًا لاحقًا.

---

# 11. Model / Provider Router

يبقى عندنا Model Registry.

مثلًا:

```text
relay/gpt-x
a6/claude-x
openrouter/gemini-x
provider-x/model-y
```

أو Aliases:

```text
shofni/coding
shofni/reasoning
shofni/fast
```

في Level 2 ممكن البداية تكون بسيطة:

```text
model ID
→ specific provider
```

وبعدين نضيف:

```text
primary
fallback1
fallback2
```

مثال:

```text
model: shofni/claude-x

primary:
  relayrouter/claude-x

fallback:
  a6api/claude-x
  openrouter/claude-x
```

وده يبقى أساس Model Router في Level 3.

---

# 12. Provider Capability Probe

أنا عايز جزء مخصوص يختبر Provider تلقائيًا.

مثلًا:

```text
Can it chat?
Can it stream?
Can it return JSON?
Can it accept tools?
Can it emit native tool calls?
Can it receive tool_result?
Can it continue after tool_result?
Can it use multiple sequential tools?
Can it use parallel tools?
```

ويطلع Report:

```text
Model Compatibility Report

Native tools:              PASS
Tool result continuation:  FAIL
Streaming:                 PASS
Responses API:             FAIL
JSON emulation:            PASS
```

وده مهم جدًا لأننا بدل ما نقعد نجرب RelayRouter يدويًا كل مرة، Gateway يعرف قدرات الـroute.

---

# 13. Diagnostic Mode

ده يبقى Feature دائم، مش مجرد MVP مؤقت.

يسجل:

```text
request_id
client_protocol
provider
model

tools_sent
tool_count

provider_native_tools
emulation_used

streaming

finish_reason

native_tool_call_received
tool_call_repaired
```

لكن **لا نسجل**:

```text
API keys
secrets
raw credentials
```

ولا محتاجين نسجل file contents بشكل افتراضي.

---

# 14. وضع Full Access اللي اتفقنا عليه

لا نضع Policy Engine يمنع التنفيذ.

في Level 2 أصلًا التنفيذ عند Client.

وفي Level 3 لاحقًا:

```text
authorization.mode = unrestricted
```

يعني:

```text
read       AUTO
write      AUTO
edit       AUTO
shell      AUTO
git        AUTO
network    AUTO
MCP        AUTO
browser    AUTO
GitHub     AUTO
Supabase   AUTO
Vercel     AUTO
```

ولا:

```text
allowlist
denylist
approval gates
branch restrictions
production restrictions
```

من Shofni.

لكن نحتفظ بـ:

```text
Schema validation
Protocol validation
Error handling
Logging
State
Recovery
```

لأن دول Reliability وليسوا Execution Restrictions.

---

# 15. أهم Abstraction لتحويل Level 2 → Level 3

دي أهم حاجة في التصميم كله:

**Tool Execution Backend.**

في Level 2:

```text
Tool Call
↓
execution_target = client
↓
Codex / Claude / OpenCode executes
```

في Level 3:

```text
Tool Call
↓
execution_target = runtime
↓
Shofni executes
```

يعني داخليًا يكون المفهوم:

```text
ToolExecutionBackend

CLIENT
RUNTIME
```

Level 2:

```text
backend = CLIENT
```

Level 3:

```text
backend = RUNTIME
```

وبالتالي الـTool Protocol كله لا يتغير.

دي النقطة التي ستوفر إعادة كتابة ضخمة لاحقًا.

---

# 16. المشروع نفسه أقترح يبقى Monorepo

تقريبًا:

```text
shofni-agent-platform/

apps/
  gateway/
  cli/

packages/

  contracts/
    messages
    tools
    models
    streaming
    errors

  client-adapters/
    openai-chat/
    openai-responses/
    anthropic-messages/

  provider-adapters/
    relayrouter/
    a6api/
    openrouter/
    openai-compatible/
    anthropic-compatible/

  router/
    model-registry
    provider-routing
    fallback

  capabilities/
    registry
    probing

  tool-compat/
    normalize
    native
    emulation
    parser
    repair

  streaming/
    normalize
    encode

  diagnostics/
    tracing
    compatibility-report

  config/

  core/
```

ثم نترك Packages مستقبلية من البداية:

```text
packages/

  agent-core/
  executor/
  task-state/
  workspace/
  recovery/
  evidence/
```

مش لازم ننفذهم الآن.

لكن الحدود المعمارية موجودة.

---

# 17. عند التحول إلى Level 3

بدل ما نغير Gateway، هنضيف:

```text
                  Existing Level 2
                       │
Clients → Gateway → Canonical Protocol
                       │
                       ↓
                  Agent Core
                       │
                 Agent Loop
                       │
              ┌────────┴────────┐
              ↓                 ↓
        Model Router      Tool Executor
              │                 │
        Providers          Local system
```

كل الآتي يظل كما هو:

```text
Client Adapters          ✅
Provider Adapters        ✅
Canonical Protocol       ✅
Model Router             ✅
Capabilities             ✅
Streaming                ✅
Tool normalization       ✅
Tool emulation           ✅
Repair                   ✅
Diagnostics              ✅
```

ونضيف فقط:

```text
Agent Loop
Tool Executor
Task State
Checkpoints
Recovery
Workspace tracking
Evidence
```

---

# 18. Durable State في Level 3

Level 2 لا يحتاج Database.

الأفضل يظل:

```text
stateless gateway
```

قدر الإمكان.

لكن من البداية نعمل abstraction:

```text
StateStore
```

وفي Level 2:

```text
MemoryStateStore
أو
NoOpStateStore
```

وعند Level 3:

```text
SQLiteStateStore
```

وبعدها لو احتجنا distributed workers:

```text
PostgreSQLStateStore
```

فالـAgent Core لا يعرف إذا كانت SQLite ولا Postgres.

---

# 19. Level 3 Database تقريبًا

لاحقًا:

```text
tasks
sessions
attempts
model_calls
tool_calls
tool_results
checkpoints
events
artifacts
```

ممكن إضافة:

```text
provider_failures
route_decisions
usage_records
```

لكن **مش هنجيب DB للمشروع في Level 2 بدون داعٍ**.

---

# 20. Error Model موحد

مهم جدًا.

بدل أن كل Provider يرجع Error مختلف:

```text
429
404 model unavailable
invalid tool schema
stream disconnected
timeout
malformed output
```

نحولهم إلى:

```text
ShofniError

PROVIDER_UNAVAILABLE
MODEL_NOT_FOUND
RATE_LIMITED
AUTH_FAILED
PROTOCOL_ERROR
TOOL_FORMAT_ERROR
STREAM_ERROR
TIMEOUT
INVALID_RESPONSE
```

وبالتالي لاحقًا Level 3 يستطيع اتخاذ قرار:

```text
retry?
fallback?
continue?
fail task?
```

بدون معرفة RelayRouter أو A6api.

---

# 21. الاختبارات التي أعتبرها إلزامية

مش مجرد Unit Tests.

نعمل Contract Tests.

مثلًا:

```text
Client protocol
   ×
Provider capability
```

نختبر:

```text
Responses → native tools provider
Responses → chat-only provider

Anthropic → OpenAI provider
Anthropic → text-only provider

Chat Completions → Anthropic provider
```

والـtool flow:

```text
Tool Call 1
↓
Tool Result
↓
Tool Call 2
↓
Tool Result
↓
Final
```

لأن **دي تحديدًا المشكلة اللي عندك حاليًا**.

واختبار:

```text
tool_call returned as text
```

واختبار:

```text
malformed JSON tool call
```

واختبار streaming أثناء tool call.

---

# 22. الشيء الذي لا أنصح به

ما نعملش من البداية:

```text
gateway.ts
```

فيه 4000 سطر وكل التحويلات جوه.

ولا:

```text
if provider === relay
if client === codex
```

في كل مكان.

لأن ده بعد شهر هيبقى:

```text
Relay × Codex
Relay × Claude
A6 × Codex
A6 × Claude
OpenRouter × OpenCode
...
```

وهنقع في combinatorial mess.

لازم دائمًا:

```text
Client
 ↓
Canonical

Canonical
 ↓
Provider
```

وبالتالي:

```text
N clients + M providers
```

بدل:

```text
N × M integrations
```

وده فرق معماري ضخم.

---

# 23. مراحل البناء التي أراها

نقسم التطوير بالشكل ده:

```text
Phase 1
Canonical Protocol
+ Error Model
+ Basic Gateway

Phase 2
Client Adapters
- Chat Completions
- Responses
- Anthropic Messages

Phase 3
Provider Adapters
- RelayRouter
- A6api
- OpenRouter
- Generic OpenAI-compatible

Phase 4
Capability Registry
+ Diagnostic Proxy
+ Compatibility Probe

Phase 5
Native Tool Normalization

Phase 6
Chat-only Tool Emulation
+ Parser
+ Repair

Phase 7
Streaming Normalization

Phase 8
Multi-provider Router
+ Fallback

Phase 9
Full Contract/E2E Test Matrix
```

وهنا يكون عندنا **Level 2 Production Architecture**.

بعدها:

```text
Phase 10
Agent Core

Phase 11
Runtime Tool Executor

Phase 12
Task State

Phase 13
Agent Loop

Phase 14
Checkpoints + Recovery

Phase 15
Workspace Tracking

Phase 16
Evidence / Audit

Phase 17
Multi-model continuation/failover
```

وهنا وصلنا **Level 3**.

---

# الصورة النهائية

الفكرة اللي أقترح نعتمدها رسميًا هي:

```text
                    SHOFNI AGENT PLATFORM

                         CLIENTS
                            │
          ┌─────────────────┼─────────────────┐
          ↓                 ↓                 ↓
        Codex          Claude Code         OpenCode
          │                 │                 │
          └────────── Client Adapters ────────┘
                            │
                            ↓
                    CANONICAL PROTOCOL
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
       Routing          Tool Compat        Streaming
          │          Native / Emulated        │
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ↓
                     Provider Router
                            │
          ┌─────────────────┼─────────────────┐
          ↓                 ↓                 ↓
    RelayRouter           A6api          OpenRouter
                                             
══════════════════════════════════════════════════════
                      LEVEL 2
══════════════════════════════════════════════════════

                            ↓

                       Agent Core
                            │
                       Agent Loop
                            │
             ┌──────────────┼──────────────┐
             ↓              ↓              ↓
        Task State      Model Router   Tool Executor
             │                             │
        Checkpoints                    Local machine
             │                         MCP / Git
        Recovery                       Browser/APIs
             │
        Evidence

══════════════════════════════════════════════════════
                      LEVEL 3
══════════════════════════════════════════════════════
```

**ده الشكل اللي أنصح نعتمد عليه من الآن.**

Level 2 لن يكون Prototype مؤقتًا؛ سيكون **Compatibility + Provider + Protocol Core الخاص بـLevel 3 نفسه**. والتحويل إلى Level 3 بعد ذلك سيكون في الأساس إضافة `Agent Core + Executor + Durable State`، بينما الجزء الأصعب الخاص بتعدد الـproviders والبروتوكولات والـtools والـstreaming سيكون بالفعل مبنيًا ومختبرًا.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)