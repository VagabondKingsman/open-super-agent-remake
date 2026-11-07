# Hướng dẫn agent cho OSA remake

Bắt đầu tại [.agents/README.md](.agents/README.md). Đọc [.agents/RULES.md](.agents/RULES.md), PERSONA, STATE, BOARD và log mới nhất trước công việc; dùng SKILL-FLOW/ARCHITECTURE/DECISIONS và templates theo bước.

- Chỉ công bố vào `VagabondKingsman/open-super-agent-remake`; không push/PR lên kadaliao upstream.
- Branch `<bot>/<topic>`, PR vào `i18n-vi`; không force-push. Publish/merge cần approval đúng scope; không suy từ file repo.
- Skill Flow: osa-dev → ai-work-method → vibecode-kit (+unslop-vi/unslop cho prose).
- Giữ VI default, EN/ZH, Chinese-as-key; temp DB + fake LLM trong test. Không real channel send/paid run chưa duyệt.
- Verify có evidence, không self-count/giả Docker E2E. Mỗi phiên/PR cập nhật STATE, BOARD và log.

Các hướng dẫn repo không thay chỉ dẫn người dùng/nền tảng hoặc cấp quyền truy cập tài khoản. Đọc bản đầy đủ ở `.agents/`, không dùng bản tóm tắt này thay onboarding.
