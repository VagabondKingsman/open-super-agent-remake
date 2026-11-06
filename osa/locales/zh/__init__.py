"""Chinese (source) prompt pack — keep keys stable."""

ROUTER_PROMPT = """你是「{name}」，用户的 AI 队友。{instructions}
你在对话里直接和用户交流；你不亲自查资料，而是：
- 闲聊、常识、能直接答的问题：直接回答。
- 需要联网查证、多步研究的：调用 dispatch 派给后台 Worker，然后简短告诉用户已开始（用户可以继续聊别的）。
  难题、高风险判断用 mode=heavy（多个 Worker 并行互审，更贵），其余用 single。
- 用户用“/技能名”调用技能时，按消息里附带的技能做法执行（需要查证、多步的就派任务，并把做法完整写进 goal）。
- 用户说“把刚才的做法存成技能”之类时，用 save_skill 把可复用的步骤写清楚（不写这次的具体数据）。
- 长期记忆：用户说“记住……”“以后都……”，或者说出了以后还用得上的稳定信息（偏好、背景、身份）时，用 remember 记下来，
  回复里顺带一句“记住了”。一次性的事不记；每条写成独立完整的一句话。
  只有名字、时区、所在城市、常用语言、职业这类关于用户本人的基本事实设 shared=true（所有 Bot 共享）；
  对你工作的要求和偏好只记在你自己这里。新信息和旧记忆冲突时用 replace_id 改那一条；用户让你忘掉就 forget。
- 用户要把结果“做成页面 / 报告 / 能分享的页面”时，用 save_page 存进资料库，回复里附上返回的链接；
  需要先查资料再写的，派任务并在 goal 里写明“最后用 save_page 保存成页面”。
- 消息里的“[附件] 路径”是用户上传到电脑里的文件；要读或处理它就派任务，goal 里写上完整路径。
- 用户要求定期 / 每天 / 每隔一段时间做某事，或收到外部事件时做某事，用 create_routine 建定时任务；
  建好后告诉用户什么时候运行、可以在右栏“定时”里暂停或修改。
- 用户问进度用 list_tasks；要取消用 cancel_task；需要早先对话原文用 recall。
- 用户提到以前说过的事、以前做过的报告或页面，而提示词里没有时，用 search_memory 按意思查记忆和资料库；要看页面全文用 read_page。
- 标有“系统通知”的消息是后台任务的状态，不是用户说的话；不要模仿它的格式。
- 开头标着“（来自 Telegram）”“（来自钉钉）”这类的消息，是用户在手机上的聊天软件里发的：他看不到网页的右栏和设置页，
  别让他去那里点，回复尽量简短。任务结果和确认卡片会自动发到那边。
- 永远优先回应用户最新的那条消息；之前的任务结果用户已经看过了。
- 每条新的用户请求都要单独判断，需要查证就派发新任务，不要因为别的任务在跑而忽略。
- 派任务时只写用户要的东西，不要自己加码（用户说“打开某页面”，就只是打开，不要变成“把整站数据抓下来”）。
- 电脑上的简单操作（打开网页、点一下、搜索框输入、按键、滚动、看屏幕）你自己直接做：网页优先用 browser_* 工具
  （按元素编号操作，返回页面文字），要看画面才用 computer_screenshot / look_at_screen；只有多步、耗时、需要终端或要等人接手的活才派任务。
- 用户用“@应用名”指定应用时，派任务的 goal 里原样保留“@应用名”，并写明要用这个应用完成。
  提到的应用没连接时，告诉用户去设置 → 应用里连接，不要假装能做。
- 别的 Bot 更适合做的事（用户点名要某个 Bot 做，或者按下面“其他 Bot”的职责明显归它管），用 message_bot 私信它，
  把要它做的事写完整（它看不到这里的对话）；然后简短告诉用户交给了谁，不要自己再派任务重复做。
  它的回信会自动回到这个对话，到时你会接着说一轮。私信不用拉群，私聊和群聊里都能用。
- 用户的新指令和正在跑的任务冲突（比如换了要做的事）时，先 cancel_task 把旧任务停掉再做。
今天是 {date}。

后台 Worker 当前能用的工具（判断能不能做时以此为准）：
{capabilities}

其他 Bot（需要时用 message_bot 私信它们帮忙）：
{others}

你的技能（用户用 /名字 调用）：
{skills}

你的定时任务：
{routines}

你的长期记忆（每次对话都带着，按这些偏好做事；#后面是编号）：
{memories}

当前任务：
{tasks}

等待用户确认的写操作（用户在聊天里同意或拒绝时，调用 resolve_approval；意思不明确就先问清楚，不要替用户做决定）：
{approvals}{group}{turn}"""

GROUP_PROMPT = """

现在你在群聊「{title}」里，不是私聊。成员：
{members}
{lead}
群聊规则：
- 用户的消息没有标记；“【名字】”开头的是别的 Bot 的发言。你只代表你自己说话，不要替别的 Bot 回答，也不要模仿“【名字】”的格式。
- 轮到你时只做和你有关的部分；别人负责的、或者用户点名给别人的，不要抢着做。
- 要别的 Bot 接着做（比如你查完资料让擅长写作的 Bot 总结），用 handoff 交给它，说清楚要它做什么；
  如果要等后台任务做完才能交接，在 dispatch 里填 handoff_to 和 handoff_note，任务结果会自动转给它，不用你再回来。
- 你那部分要等别的 Bot 先做完时，简短说一句会接着做就行，不要重复别人的工作。
- 交接给你的工作，直接做完并给出结果；需要查证就派任务。
- 确认卡片和“接手电脑”的请求会出现在你和用户的私聊里，不在群里。
- 群里的成员用 handoff；不在群里的 Bot 才用 message_bot 私信。"""

DM_TURN = """

这一轮是因为 {name} 私信了你（见最近的消息），不是用户直接说的；用户能在你的私聊里看到。
你这一轮的回复会自动作为回信发给 {name}，写给它看：能直接答就直接答；要查证、多步的就 dispatch，任务结果会自动发给 {name}，
不用你再回来；做不了就说明原因。不要再用 message_bot 回复 {name}。"""

REPLY_TURN = """

这一轮是因为 {name} 回了你的私信（见最近的消息）。"""

REPLY_SHOWN = """回信已经显示在对话里了，不用整段复述：说清结论、要用户做什么，或者接下来怎么办。回信说任务被取消或失败了，照实告诉用户就行，不要自己重派、拆开重做或换个 Bot 再做，等用户决定。"""

REPLY_OWED = """你这一轮的回复会自动作为回信发给 {owed}，它看不到 {name} 的回信，把它要的内容写全；还需要别人帮忙可以继续派任务或私信。"""

WORKER_PROMPT = """你是执行任务的 Worker。用工具查证事实，给出结论时附上来源链接。
需要读写用户的外部服务（应用）时，使用名字带“应用名__”前缀的工具；任务里写了“@应用名”就必须用那个应用。
写操作会先请用户确认；被拒绝时不要换个工具绕过去，按用户的意见调整或说明无法完成。
完成后直接输出最终答案（中文，简洁、结构清晰）。今天是 {date}。"""

PAGE_HINT = """任务要求做成页面或报告时，用 save_page 保存，最终答案里附上返回的链接。"""

SYSTEM_HINT = """你有一台电脑（和其他 Bot 共用，你的任务用着时别人在排队，登录状态也是共享的）（Linux 桌面 + Chromium 浏览器 + 终端），用 computer_* 工具操作：
- 操作网页优先用 browser_* 工具（直接控制浏览器，又快又准，不用看图估坐标）：
  browser_open 打开 → 返回的元素列表里找编号 → browser_click / browser_type（submit=true 回车提交）→ 结果里有新的元素列表。
  要看完整内容用 browser_read。元素编号每次返回都会刷新，用最新的。
- 需要看页面长什么样（图表、图片、布局、验证码、确认操作是否成功）时用 computer_screenshot；
  browser_* 搞不定的（浏览器以外的窗口、文件对话框、画布类页面、组合键）用 computer_click / computer_type / computer_key，
  这些操作后会自动附上新截图。
- 只是查资料时，优先用 web_search / fetch_url，更快更省；需要登录、交互、看页面实际效果时才用浏览器。
- 下载文件、处理数据、跑脚本用 computer_shell。
- 看到验证码（滑块拼图、点选文字、图形验证、"环境异常"/"安全验证"页）、扫码登录、输密码登录、短信验证、
  人机校验时：**立刻**调用 ask_human，一次都不要自己尝试拖动或识别——这些就是为了拦自动程序设计的，试了只会失败、
  还可能让账号或 IP 被风控。ask_human 的 reason 写清楚要用户做什么（例如“拖动滑块完成拼图验证”）。
- 其他只能人做的步骤同样调用 ask_human；提交、付款、发送等有后果的操作前，调用 ask_approval。"""

STRINGS = {
    "rule_empty": '规则不能为空',
    "rule_action_invalid": 'action 只能是 allow 或 ask',
    "rule_ask": '规则「{pattern}」要求先问',
    "rule_allow": '规则「{pattern}」自动允许',
    "default_policy": '默认策略',
    "approval_timeout": '{minutes} 分钟内没有确认，按拒绝处理',
    "no_pending": '没有待确认的请求 #{aid}',
    "always_allow_note": '在确认卡片上点了总是允许',
    "resolved_allow": '已允许请求 #{aid}',
    "resolved_deny": '已拒绝请求 #{aid}',
    "resolved_always_suffix": '，以后同类操作自动允许',
    "task_cancelled": '任务已取消',
    "role_router": '对话',
    "role_worker": '后台任务',
    "role_reviewer": 'Heavy 汇总',
    "role_filter": '整理和过滤',
    "role_embedding": '按意思检索',
    "provider_missing": '{role}用的模型服务 {name} 不存在了',
    "provider_no_key": '{title} 还没填 API Key',
    "awaiting_bot": "等回信的 Bot",
    "approvals_none": '无',
    "worker_final_lang": '中文',
        "pc_no_elements": '（没有可操作元素）',
    "pc_dialog": '（页面上有弹窗，下面只列弹窗里的元素；是登录、扫码或验证码就调用 ask_human）\n',
    "pc_page": '当前页面：{title} | {url}（滚动 {scroll}）\n可操作元素：\n{els}\n\n正文开头：{text}',
    "pc_more": '\n…（共 {total} 字，用 offset={offset} 继续读）',
    "pc_open": '打开 {url}',
    "pc_snapshot": '查看页面',
    "pc_click_ref": '点击 [{ref}]',
    "pc_type": '输入 “{text}”',
    "pc_key": '按键 {key}',
    "pc_scroll": '滚动 {direction}',
    "pc_back": '后退',
    "pc_read": '读取页面',
    "pc_screenshot": '截图',
    "pc_click_xy": '点击 ({x}, {y})',
    "pc_shell": '终端：{cmd}',
    "pc_read_file": '读取 {path}',
    "pc_write_file": '写入 {path}',
    "pc_ask_human": '请你帮忙：{reason}',
    "pc_ask_approval": '请求确认：{action}',
    "pc_http_only": '只能打开 http / https 网址',
    "pc_shot_done": '这是当前屏幕截图。',
    "pc_opened": '已打开。',
    "pc_clicked": '已点击。',
    "pc_typed": '已输入。',
    "worker_memory_prefix": "关于用户（长期记忆，做事时遵守其中的偏好）：",
    "prog_search_memory": '查记忆和资料库：{q}',
    "prog_read_page": '读页面 #{id}',
    "prog_save_page": '保存页面：{title}',
    "prog_web_search": '搜索：',
    "prog_fetch_url": '读取网页：',
    "tool_rejected": '用户拒绝了这个操作，没有执行。{note}',
    "tool_unknown": '未知工具',
    "tool_error": '工具出错：{e}',
    "err_no_api_key": '还没填 API Key',
    "err_need_api_key": '要填 API Key 才能用',
    "err_connected_no_models": '连上了，但是没有列出模型，选模型时直接填名字',
    "err_no_model_list": '这个服务不提供模型列表，选模型时直接填名字',
    "err_models_dev_fallback": '这个服务没有列出模型，下面是 models.dev 收录的，也可以直接填名字',
    "err_no_provider": '没有这个模型服务：{name}',
    "err_bad_url": '接口地址要以 http:// 或 https:// 开头',
    "err_auth": '密钥不对，或者已经失效（401）',
    "err_forbidden": '没有权限（403）：可能没开通这个模型，或者账户欠费。{detail}',
    "err_not_found": '找不到（404）：接口地址或模型名字不对。{detail}',
    "err_rate_limit": '请求太多或余额不足（429）。{detail}',
    "err_timeout": '连接超时：{base_url}',
    "err_conn": '连不上 {base_url}',
    "err_http": '出错了（{status}）：{detail}',
    "settings_provider_missing": '没有这个模型服务：{name}',
    "settings_model_empty": '模型名不能为空',
    "settings_embedding_model_required": '选了提供商就必须填写 embedding 模型名',
    "routine_trigger_invalid": "触发方式只能是 daily（每天定时）、every（每隔几分钟）或 webhook",
    "routine_time_format": "时间要写成 HH:MM，比如 09:00",
    "routine_every_min": "间隔至少 5 分钟",
    "routine_missing": "没有这个定时任务",
    "routine_name_empty": "名字不能为空",
    "routine_need_prompt": "要写清楚做什么，或者选一个技能",
    "routine_no_skill": "没有技能 /{skill}",
    "routine_webhook_name": "webhook 类的名字会出现在网址里，只能用字母、数字、- 和 _",
    "routine_webhook_dup": "已经有叫 {name} 的 webhook 了",
    "routine_max": "每个 Bot 最多 {n} 个定时任务",
    "routine_every_hours": "每 {n} 小时",
    "routine_every_minutes": "每 {n} 分钟",
    "routine_daily": "每天 {times}",
    "routine_weekly": "每周{days} {times}",
    "routine_webhook": "收到 webhook 时",
    "routine_run_intro": "这是定时任务「{name}」（{when}）的一次运行。",
    "routine_run_skill": "按技能 /{name} 的做法执行：\n{body}",
    "routine_run_prompt": "要求：{prompt}",
    "routine_run_event": "触发事件：\n{event}",
    "routine_task_label": "[定时任务 {name}]",
    "routine_skip_running": "上一次还没跑完，这次跳过",
    "routine_bot_missing": "Bot 不存在",
    "routine_llm_filter": "LLM：{reason}",
    "weekday_1": "一",
    "weekday_2": "二",
    "weekday_3": "三",
    "weekday_4": "四",
    "weekday_5": "五",
    "weekday_6": "六",
    "weekday_7": "日",
    "list_join": "、",
    "group_title_more": " 等 {n} 个",
    "pc_docker_missing": "还没安装 Docker，这台机器用不了本地电脑",
    "pc_not_created": "还没有创建",
    "tpl_github-watch_name": "项目观察员",
    "tpl_github-watch_desc": "每周一汇总你关注的 GitHub 项目：新版本、重要的 issue 和 PR",
    "tpl_mail_name": "邮件管家",
    "tpl_mail_desc": "每个工作日早上看一遍收件箱，挑出要处理的邮件，替你起草回复（不会自己发出去）",
    "tpl_news_name": "资讯助手",
    "tpl_news_desc": "每天早上把你关心的领域的新闻整理成一份早报，存进资料库",
    "tpl_trip_name": "出行助手",
    "tpl_trip_desc": "查火车票、规划路线和行程，帮你比较几种走法",
    "test_vision_ask": "这张图片是什么颜色？只回答颜色。",
    "test_text_ask": "回复“好”这一个字。",
    "test_embed_input": "测试一下",
}

