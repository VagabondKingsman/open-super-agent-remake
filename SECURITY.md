# 安全说明

## 当前的安全边界

- **登录鉴权要自己打开。** 设置环境变量 `OSA_PASSWORD` 后，除登录页、分享链接、webhook 和前端静态文件外，页面、接口和 WebSocket 都要先登录；
  只有一个密码，没有多用户和权限区分。**不设置时不用登录**，能访问到这个端口的人就能和你的 Bot 对话、操作电脑、使用你接入的应用，
  这时请只在本机或内网（例如 Tailscale）使用。部署到公网时务必设置一个足够长的随机密码，并通过 HTTPS 访问。
- 登录状态是一个签了名的 HttpOnly cookie（SameSite=Lax，HTTPS 下带 Secure），签名密钥在 `data/session.key`。同一个 IP 10 分钟内输错 5 次会暂停登录。
  另外所有来源的密码校验排成一队，输错一次占 1 秒，所以换 IP 或伪造 `X-Forwarded-For` 也只能每秒试一次左右；排队的超过 8 个时直接回“请求太多”，不校验。
- 来源（Origin）和本站不一致的写请求与 WebSocket 一律拒绝，不管开没开登录，webhook 也一样。所以你在浏览器里打开的网页，没法连上本机的服务替你发消息、处理确认卡片。
- 没开登录时，只接受用 `localhost`、IP 地址、`*.local`、`*.ts.net` 和 `server.allowed_hosts` 里的名字访问，防 DNS rebinding（别人把自己的域名解析到 127.0.0.1，借你的浏览器读写本机的服务）。
- 本地电脑的 VNC 没有密码，只监听电脑容器里的 127.0.0.1，不映射到宿主机端口，由服务端经 `docker exec` 转发给浏览器。电脑里 Chromium 的 DevTools 端口（9222）只监听电脑内部，也不做端口映射。
- 用 Docker Compose 部署时，默认不挂宿主机的 `docker.sock`。要用本地电脑得加上 `compose.computer.yaml`，这时服务等于有宿主机的 root 权限；服务里运行的第三方应用（MCP）也在这个容器里，请只添加信得过的应用。只用 Instabox 就不要加。
- 模型提供方的密钥只从环境变量读取。应用密钥可以存进保险库：用 Fernet 加密写进数据库，主密钥来自 `OSA_VAULT_KEY` 或 `data/vault.key`（权限 600）。两样都要妥善保管，`data/` 不进 git。
- 接口和模型只能看到保险库里密钥的名字；明文只在启动应用时注入它的进程环境变量。
- 设置了 `OSA_WEBHOOK_TOKEN` 后，webhook 必须带上 `X-OSA-Token` 才会被接受；没设置时只接受本机请求。
- 电脑里的浏览器登录状态由所有 Bot 共享，请留意让它登录了哪些账号。
- 页面的分享链接（`/s/<token>`）只是一个不可猜的地址，取消分享后失效。没设置 `OSA_PASSWORD` 时，“未分享”的页面同样能被访问到这个端口的人看到。
- Bot 生成的 HTML 页面在沙箱里显示：带 CSP 的 `sandbox` 和 `connect-src 'none'`，脚本拿不到本站的数据，也不能调接口或连 WebSocket（服务端还会拒绝来源为 `null` 的 WebSocket）。
- 资料库的文件接口只能访问共用电脑里的 `/data/workspace`。
- “演示一遍”会记下你在浏览器里点了什么、输入了什么。密码框和名字像密码、验证码、卡号的输入框只记 `******`，但这是按输入框判断的，
  录制时请不要在普通输入框里填敏感信息。录到的步骤会交给模型写技能草稿。
- **网页里的提示注入**：Bot 读到的网页、邮件、webhook 内容里可能藏着“去做某事”的指令。对此有两条防线：
  - `fetch_url` 默认不抓本机和内网地址（回环、内网、链路本地、云服务器的元数据地址 `169.254.169.254`、100.64/10），解析到内网的域名和跳转到内网的也挡住；
    要抓内网页面在 `config.yaml` 里设 `tools.fetch_private: true`。检查和真正连接之间域名还可能换地址（DNS rebinding），这一点没有防。
  - 写操作要先过确认卡片（见设置里的确认规则）。
  - 定时任务、webhook 触发的后台任务没人盯着，读到的内容又最容易带注入：在 Docker、Instabox 的电脑里执行终端命令（`computer_shell`）、写文件（`computer_write_file`）前都要确认，
    卡片超时按拒绝处理。对话里派的任务照旧不问。确认规则里的“自动允许”（比如 `computer_shell:git *`）对后台任务同样有效。
- **电脑里能连到什么**：
  - 本地电脑的容器带 `--security-opt no-new-privileges`、`--pids-limit 4096`，去掉了 `NET_RAW`、`MKNOD` 两个权限。只对新建的容器生效，已有的 `osa-computer` 要删掉重建（`docker rm -f osa-computer`，`/data` 在卷里不会丢）。
  - macOS 的 Docker Desktop 上（2026-11-06 实测），本地电脑能通过 `host.docker.internal` 连到宿主机上**只监听 127.0.0.1 的服务**，
    宿主机看到的来源也是 127.0.0.1，和你自己的浏览器分不出来。所以在 Mac 上不设 `OSA_PASSWORD` 时，Bot 在电脑终端或浏览器里能直接调用本服务的接口
    （包括处理确认卡片），网页里的提示注入可以借此绕过确认。用 Docker Compose 跑、端口映射到 127.0.0.1 时应该也一样（没有单独测）。
    **在 Mac 上用本地电脑时请设置 `OSA_PASSWORD`**，或改用 Instabox。
  - Linux 上（按 Docker 默认的网络隔离推断，没有实测）：电脑容器在默认网络里，连不到宿主机只监听 127.0.0.1 的端口，也连不到 Docker Compose 网络里的服务容器；
    但在云服务器上一般能连到云厂商的元数据地址（阿里云 `100.100.100.200`、腾讯云、AWS 的 IMDSv1 等）。服务器绑了带权限的角色时，请改用 Instabox 或在云厂商那边关掉元数据访问。
- 推送内容（标题和一两句摘要）经浏览器厂商的推送服务转发，按 RFC 8291 端到端加密，推送服务只看得到密文和设备地址。VAPID 私钥存在数据库里。

## 报告漏洞

请**不要**为安全问题公开提 issue。请通过 GitHub 的 [Private vulnerability reporting](https://github.com/kadaliao/open-super-agent/security/advisories/new) 私下报告。
