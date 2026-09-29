# Paper Metadata Skill

[English](#english) | [中文](#中文)

## English

Extract metadata from PDF and Word papers using **your current Codex session**. No separate model API key is needed in the default workflow.

Local Python helpers read documents and validate/export results. Codex extracts titles, authors, affiliations, original abstracts and keywords in small batches. The helpers do not access Codex credentials, launch another model, or call a model API.

### Install for Codex

Download this entire repository into a supported skill folder, for example:

```text
~/.agents/skills/paper-metadata/
```

On Windows, this is typically `C:\Users\YOUR_NAME\.agents\skills\paper-metadata\`. For a project-only installation, use `<project>/.agents/skills/paper-metadata/`. Keep all Python files and `SKILL.md` together.

Requires Python 3.10+. Install document-reading dependencies in the Python environment Codex will use:

```bash
python -m pip install -r requirements.txt
```

No `.env` is required. In Codex CLI, use `/skills` to check discovery, then ask:

```text
$paper-metadata Extract metadata from D:\papers, including subfolders,
and save JSONL and CSV results in D:\results.
Use the current session; do not call a separate model API.
```

If the skill does not appear, restart Codex. See the [official skill documentation](https://learn.chatgpt.com/docs/build-skills).

### How it works

1. **Prepare locally:** read all supported files and save text excerpts in a task directory.
2. **Extract in batches:** Codex reads 10 papers by default, automatically expanding to at most 20 when each excerpt is no longer than 6000 characters, with a total 180000-character budget, and writes one batch of structured metadata.
3. **Save and resume:** the helper validates and checkpoints results per paper. A later session can resume unfinished work.
4. **Export:** generate JSONL or CSV with completion and missing-field counts.

The fast defaults read the first 3 PDF pages and up to 12000 characters per document. Increase limits for papers with long front matter. A batch may contain fewer than 10 papers to fit its budget; an unusually long single excerpt is kept intact. This reduces tool round trips, but does not guarantee a particular processing speed.

### Local helper commands

These commands support the agent workflow; running them alone does **not** perform AI extraction.

```bash
python paper_local.py prepare /path/to/papers --work-dir /path/to/task --recursive
python paper_local.py next --work-dir /path/to/task --max-batch-chars 180000
# Codex writes batch.json using the returned paper IDs and text.
python paper_local.py save --work-dir /path/to/task --metadata /path/to/task/batch.json
# Repeat next + extraction + save until done=true.
python paper_local.py export --work-dir /path/to/task --output /path/to/results.jsonl
python paper_local.py export --work-dir /path/to/task --output /path/to/results.csv --format csv
```

Use a **new** task directory for `prepare`. To resume, call `next` on the existing directory. Use `--max-pages 8 --max-chars 24000` on `prepare` when needed. Existing exports are not overwritten. Set `--batch-size 15` on `next` to use a fixed limit instead of automatic expansion. Character counts are not token counts; reduce the budget if the host truncates tool output or generated results.

The batch JSON schema and complete operating instructions are in [SKILL.md](SKILL.md).

### Results and limitations

- Fields: `file`, `sha256`, `status`, `title`, `authors`, `schools`, `abstract`, `keywords`, `missing_fields`, `error`.
- Statuses: `ok`, `needs_review` (missing fields), `error` (document reading failed), and `pending` (not yet processed).
- Validation checks structure and source changes, not factual accuracy. Review important metadata against the original.
- Original abstracts are preserved; missing fields are not invented. PDF layout or truncated front matter can affect results.
- Scanned PDFs require separate OCR. Legacy DOC requires Windows, Microsoft Word and optional `pywin32`.
- Extraction uses the host assistant's normal usage limits and context. With a subscription-authenticated Codex session, it is part of that session's usage; this tool does not grant or bypass an allowance. API-authenticated sessions retain their own billing arrangements.
- Document text is read by the host assistant, so this is not a fully offline extraction workflow.
- Keep task directories outside the skill repository: they contain manuscript excerpts and results.
- Other agents need skill support, local file access and Python command execution. DeepSeekHarness compatibility has not been verified.

### Optional standalone API mode

The original API script is retained for users who explicitly want unattended API batches:

```bash
python -m pip install -r requirements-api.txt
```

Copy `.env.example` to `.env`, then set `LLM_API_KEY`, `LLM_BASE_URL` and `LLM_MODEL`. The base URL must omit `/chat/completions`. Legacy `DEEPSEEK_API_KEY` and `DEEPSEEK_MODEL` remain supported.

```bash
python extract_paper_metadata.py /path/to/papers --recursive --resume
python extract_paper_metadata.py /path/to/papers --format csv -o outputs/papers.csv
```

This optional mode uses a separately configured OpenAI-compatible API and its billing. It is **not** required for the Codex skill. Its JSONL resume uses file paths, not content fingerprints; CSV does not support resume. Without `--resume`, API mode overwrites its selected output. Use `--no-json-mode` if the provider does not support `response_format`.

### Tests

```bash
# Local workflow tests (document dependencies only)
python -m unittest discover -s tests -p test_local.py -v
# All tests, after installing requirements-api.txt
python -m unittest discover -s tests -v
```

Tests use temporary documents and mocked API responses, with no paid model calls.

---

## 中文

使用**当前 Codex 会话**批量提取 PDF 和 Word 论文信息。默认方式**无需额外配置模型 API 密钥**。

本地 Python 程序负责读取文档、校验和导出；Codex 负责分批提取标题、作者、单位、摘要原文和关键词。程序不读取 Codex 登录凭据、不启动另一个模型，也不调用模型 API。

### 安装到 Codex

将整个仓库下载到支持的技能目录，例如：

```text
~/.agents/skills/paper-metadata/
```

Windows 通常对应 `C:\Users\你的用户名\.agents\skills\paper-metadata\`。仅供当前项目使用时，可放在 `<项目>/.agents/skills/paper-metadata/`。所有 Python 文件与 `SKILL.md` 应保留在同一个目录。

需要 Python 3.10 或更新版本。在 Codex 实际使用的 Python 环境中安装文档读取依赖：

```bash
python -m pip install -r requirements.txt
```

**不需要配置 `.env`。** 在 Codex CLI 中用 `/skills` 检查是否发现技能，然后直接提出：

```text
$paper-metadata 整理 D:\papers 中的论文，包含子目录，
在 D:\results 中保存 JSONL 和 CSV。
使用当前会话提取，不调用额外的模型 API。
```

如果技能未出现，可重启 Codex。安装机制见 [官方技能说明](https://learn.chatgpt.com/docs/build-skills)。

### 工作方式与速度

1. **本地预处理：** 一次读取所有支持的文档，把文本片段存入任务目录。
2. **小批次提取：** Codex 默认每批处理 10 篇；当批内每篇片段都不超过 6000 字符时，自动扩展到最多 20 篇。默认每批总文本预算为 180000 字符，一次写出整批元数据。
3. **保存进度：** 程序逐篇校验并保存结果，中断后可以继续未完成的部分。
4. **统一导出：** 输出 JSONL 或 CSV，并统计完成、缺失和失败项。

快速模式默认读取 PDF 前 3 页，每篇最多 12000 字符。论文前置内容较长时可以提高上限。总文本较多时，一批可能少于 10 篇；特别长的单篇片段保留完整。分批方式减少工具交互次数，实际速度仍取决于论文长度和 Codex 响应速度。

### 本地辅助命令

以下命令供助手协作使用，**仅运行这些命令不会自动完成 AI 提取**：

```bash
python paper_local.py prepare /path/to/papers --work-dir /path/to/task --recursive
python paper_local.py next --work-dir /path/to/task --max-batch-chars 180000
# Codex 根据返回的论文 ID 和文本，写出 batch.json。
python paper_local.py save --work-dir /path/to/task --metadata /path/to/task/batch.json
# 重复获取批次、提取和保存，直到 done=true。
python paper_local.py export --work-dir /path/to/task --output /path/to/results.jsonl
python paper_local.py export --work-dir /path/to/task --output /path/to/results.csv --format csv
```

将示例路径替换为本机路径。`prepare` 必须使用新任务目录；续跑时直接对原目录执行 `next`。需要更多正文时，准备阶段可使用 `--max-pages 8 --max-chars 24000`。导出不会覆盖已有文件。对 `next` 指定 `--batch-size 15` 可以固定批次上限并关闭自动扩展。字符数不等于 token 数；如果助手的工具输出或生成结果被截断，应降低批次预算。

批次 JSON 格式及完整操作流程见 [SKILL.md](SKILL.md)。

### 输出与限制

- 输出字段：`file`、`sha256`、`status`、`title`、`authors`、`schools`、`abstract`、`keywords`、`missing_fields`、`error`。
- 状态包括：`ok`、`needs_review`（字段缺失）、`error`（文档读取失败）、`pending`（尚未处理）。
- 程序校验格式及来源文件是否变动，不保证提取内容准确，重要字段需要对照原文核查。
- 保留摘要原文，不编造缺失信息；PDF 排版和读取范围可能影响结果。
- 扫描 PDF 需要另行 OCR；旧版 DOC 需要 Windows、Microsoft Word 和可选依赖 `pywin32`。
- 提取使用当前助手的正常额度与上下文。通过订阅账户登录 Codex 时，属于当前会话的使用；本工具不会额外提供或绕过额度。使用 API 登录的会话仍遵循其计费方式。
- 文本会由当前助手读取，因此不是完全离线的提取流程。
- 任务目录包含论文片段与结果，应保存在技能仓库之外。
- 其他助手需支持技能、本地文件访问和 Python 执行；尚未验证 DeepSeekHarness 的兼容性。

### 可选：独立 API 模式

保留原脚本，供明确希望使用独立 API 批处理的用户选择：

```bash
python -m pip install -r requirements-api.txt
```

复制 `.env.example` 为 `.env`，填写 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`。基础地址不应包含 `/chat/completions`。旧配置 `DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL` 仍然支持。

```bash
python extract_paper_metadata.py /path/to/papers --recursive --resume
python extract_paper_metadata.py /path/to/papers --format csv -o outputs/papers.csv
```

此模式使用单独配置的 OpenAI 兼容 API，并按服务商规则计费，**Codex 技能不需要使用此模式**。其 JSONL 续跑按路径判断，不检测文件内容更新；CSV 不支持续跑。不使用 `--resume` 会覆盖指定输出。接口不支持 `response_format` 时，可加 `--no-json-mode`。

### 测试

```bash
# 本地工作流测试，仅需要文档读取依赖
python -m unittest discover -s tests -p test_local.py -v
# 安装 requirements-api.txt 后运行全部测试
python -m unittest discover -s tests -v
```

测试使用临时文档及模拟 API 响应，不调用付费模型。
