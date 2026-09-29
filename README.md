# Paper Metadata · 论文元数据提取 Skill

批量读取 PDF、DOCX、DOC，提取标题、作者、单位、摘要原文和关键词，导出 JSONL 或 CSV。既可独立运行，也可作为支持 SKILL.md 的 AI 助手技能使用。

支持 DeepSeek 及提供 OpenAI 兼容 Chat Completions 接口的服务。通过 API 基础地址、模型名和密钥切换；不包含 Claude/Gemini 原生协议适配。

## 作为 Skill 使用

将整个仓库放入助手支持的技能目录，目录名建议为 `paper-metadata`，保留根目录的 `SKILL.md` 和脚本。安装方式取决于助手；上传 GitHub 不代表所有模型都会自动发现它。

安装依赖、配置 API 后，可以对支持此技能的助手说：

> 使用 paper-metadata，整理 D:\papers 中的论文，递归处理子目录，保存到 D:\results\papers.jsonl。

不支持 Skill 的助手，也可以在具备本地文件访问与命令执行能力的环境中阅读说明并调用脚本。此仓库不是在线 API 服务。

## 安装配置

需要 Python 3.10 或更新版本。在仓库目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`：

```dotenv
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

其他服务请填其文档提供的兼容接口基础地址和模型名。脚本会在地址后添加 `/chat/completions`，不要重复填写。

原有 `DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL` 仍然支持，新变量优先。已有环境变量优先于 `.env`。不要提交真实密钥或论文。读取旧版 DOC 还需要 Windows、Microsoft Word 和可选依赖 `pip install pywin32`。

## 使用

```powershell
# 默认输出 outputs/paper_metadata.jsonl
python extract_paper_metadata.py "D:\papers"

# 递归处理、断点续跑
python extract_paper_metadata.py "D:\papers" --recursive --resume

# CSV 可用 Excel 导入
python extract_paper_metadata.py "D:\papers" --format csv -o outputs/paper_metadata.csv

# 自定义 API，密钥从指定环境变量读取
python extract_paper_metadata.py "D:\papers" --base-url "https://api.example.com/v1" --model "your-model" --api-key-env OTHER_API_KEY

# 接口不支持 response_format 时关闭 JSON 模式
python extract_paper_metadata.py "D:\papers" --no-json-mode

# 调整读取范围
python extract_paper_metadata.py "D:\papers" --max-pages 12 --max-chars 36000
```

完整参数见 `python extract_paper_metadata.py --help`。默认超时 90 秒、文件间隔 0.3 秒，可用 `--timeout`、`--sleep` 调整。

## 输出与限制

结果包含 `file`、`status`、`title`、`authors`、`schools`、`abstract`、`keywords`、`error`。列表字段在 CSV 中用分号连接。

- JSONL 逐篇保存。`--resume` 按文件路径跳过成功项，失败项重试后追加记录；不检测文件内容更新。
- 不使用 `--resume` 会覆盖同名输出。CSV 在整个批次结束后保存，不支持续跑。
- 默认读取 PDF 前 8 页、最多发送 24000 字符。扫描 PDF 需要先 OCR。
- `status=ok` 表示获得非空结果，不保证信息完整或准确；重要字段请核对原文。
- 论文文本会发送至配置的 API，费用与数据处理方式取决于该服务。建议先试少量文件。
- 不可信文档内容导入表格软件时，按文本导入，避免被解释为公式。

## 开发检查

测试使用模拟响应，不调用付费 API：

```powershell
python -m unittest discover -s tests -v
```
