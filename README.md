# Paper Metadata Skill

[English](#english) | [中文](#中文)

## English

A lightweight AI skill for batch extracting metadata from research papers. Read PDF and Word documents, extract titles, authors, affiliations, original abstracts, and keywords, and export the results as JSONL or CSV.

Use it as a standalone Python tool or as a skill in an AI assistant that supports `SKILL.md`.

### Features

- Batch processing of PDF, DOCX, and DOC files.
- Optional recursive folder scanning.
- Configurable OpenAI-compatible Chat Completions APIs, including DeepSeek.
- JSONL output with resume support.
- CSV export for Excel and other spreadsheet applications.
- Original abstract extraction rather than AI-generated summaries.

Native Claude and Gemini API protocols are not included. Other providers must offer a compatible Chat Completions endpoint.

### Use as a Skill

Place the entire repository in a skill directory supported by your assistant. The recommended folder name is `paper-metadata`. Keep `SKILL.md` and the Python script at its root.

After installing dependencies and configuring your API, ask your assistant:

> Use paper-metadata to extract metadata from the papers in D:\papers, including subfolders, and save the results to D:\results\papers.jsonl.

Installation and discovery depend on the assistant. Publishing the repository on GitHub does not automatically make it available to every model.

An assistant without skill support can still follow this README if it can access local files and run Python commands. This repository is not a hosted API service.

### Installation

Requires **Python 3.10 or later**.

Download or clone the repository, then run these commands from its directory.

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Legacy `.doc` support additionally requires **Windows**, **Microsoft Word**, and the optional dependency:

```bash
pip install pywin32
```

PDF and DOCX processing does not require Microsoft Word.

### API Configuration

Edit `.env`:

```dotenv
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

For another provider, use its compatible API base URL and model name:

```dotenv
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=your-model
```

The script appends `/chat/completions` to the base URL. Do not include that suffix yourself.

The legacy variables `DEEPSEEK_API_KEY` and `DEEPSEEK_MODEL` remain supported. The new variables take precedence. Existing environment variables take precedence over values loaded from `.env`.

Do not commit real API keys or private papers.

### Usage

The examples below use Windows paths. On macOS or Linux, replace `D:\papers` with your local folder path, such as `/home/you/papers`.

**Process a folder:**

```powershell
python extract_paper_metadata.py "D:\papers"
```

Default output:

```text
outputs/paper_metadata.jsonl
```

**Include subfolders:**

```powershell
python extract_paper_metadata.py "D:\papers" --recursive
```

**Resume and skip previously successful files:**

```powershell
python extract_paper_metadata.py "D:\papers" --recursive --resume
```

**Export CSV:**

```powershell
python extract_paper_metadata.py "D:\papers" --format csv -o outputs/paper_metadata.csv
```

**Use another API and read its key from a named environment variable:**

```powershell
python extract_paper_metadata.py "D:\papers" --base-url "https://api.example.com/v1" --model "your-model" --api-key-env OTHER_API_KEY
```

Set `OTHER_API_KEY` in your environment or `.env` before running this command.

**Disable JSON mode if the provider does not support `response_format`:**

```powershell
python extract_paper_metadata.py "D:\papers" --no-json-mode
```

**Read more pages and allow a longer text excerpt:**

```powershell
python extract_paper_metadata.py "D:\papers" --max-pages 12 --max-chars 36000
```

**View all options:**

```powershell
python extract_paper_metadata.py --help
```

The default request timeout is 90 seconds, with a 0.3-second pause between files. Adjust these with `--timeout` and `--sleep`.

### Output

Each record contains:

| Field | Description |
| --- | --- |
| `file` | Source file path |
| `status` | Processing status: `ok` or `error` |
| `title` | Paper title |
| `authors` | Author names |
| `schools` | Universities, institutions, or other affiliations |
| `abstract` | Original abstract |
| `keywords` | Keywords |
| `error` | Error message, if processing failed |

Authors, affiliations, and keywords are lists in JSONL and semicolon-separated values in CSV.

### Notes and Limitations

- JSONL records are saved after each file. `--resume` skips successful files by path and appends new records for retried failures.
- Resume does not detect changes to file contents. Use a new output file when reprocessing modified papers.
- Running without `--resume` overwrites the selected output file.
- CSV is written after the entire batch finishes and does not support resume.
- By default, the tool reads the first 8 PDF pages and sends up to 24,000 characters per paper.
- Scanned PDFs require OCR beforehand. OCR is not included.
- `status=ok` means a nonempty result was returned, not that every field is complete or correct. Check important information against the source document.
- Extracted text is sent to your configured API. Costs and data handling depend on the provider. Try a small batch first.
- Import untrusted document content into spreadsheet applications as text to avoid interpreting it as formulas.

### Development Checks

Tests use mocked responses and do not call paid APIs:

```bash
python -m unittest discover -s tests -v
```

---

## 中文

一个轻量级论文元数据提取 Skill。支持批量读取 PDF 和 Word 文档，提取标题、作者、单位、摘要原文和关键词，导出 JSONL 或 CSV。

既可以作为独立 Python 工具运行，也可以作为支持 `SKILL.md` 的 AI 助手技能使用。

### 功能特点

- 批量处理 PDF、DOCX 和 DOC 文件。
- 支持递归扫描子文件夹。
- 支持 DeepSeek 及其他 OpenAI 兼容 Chat Completions API。
- 支持 JSONL 输出和断点续跑。
- 支持 CSV 导出，方便用 Excel 等表格软件查看。
- 提取论文摘要原文，不将模型生成的概述混作原文摘要。

目前不包含 Claude、Gemini 原生 API 协议适配。其他服务需要提供兼容的 Chat Completions 接口。

### 作为 Skill 使用

将整个仓库放入助手支持的技能目录，目录名建议为 `paper-metadata`。保留根目录中的 `SKILL.md` 和 Python 脚本。

安装依赖、配置 API 后，可以向助手提出：

> 使用 paper-metadata，整理 D:\papers 中的论文，递归处理子目录，保存到 D:\results\papers.jsonl。

具体安装和发现方式取决于助手。上传到 GitHub 并不意味着所有模型都会自动发现或调用这个技能。

不支持 Skill 的助手，也可以在具备本地文件访问和 Python 命令执行能力的环境中，按照本说明调用脚本。本仓库不是在线 API 服务。

### 安装

需要 **Python 3.10 或更新版本**。

下载或克隆仓库后，在仓库目录运行以下命令。

**Windows PowerShell：**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

**macOS / Linux：**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

读取旧版 `.doc` 文件还需要 **Windows**、**Microsoft Word** 和以下可选依赖：

```bash
pip install pywin32
```

处理 PDF 和 DOCX 不需要安装 Microsoft Word。

### API 配置

编辑 `.env`：

```dotenv
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

使用其他服务时，填写其兼容接口基础地址和模型名：

```dotenv
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=your-model
```

脚本会自动在基础地址后添加 `/chat/completions`，不要重复填写这一部分。

原有的 `DEEPSEEK_API_KEY` 和 `DEEPSEEK_MODEL` 仍然支持，新变量优先。已有环境变量优先于 `.env` 中的配置。

不要将真实 API 密钥或私有论文提交到仓库。

### 使用方法

以下示例使用 Windows 路径。macOS 或 Linux 用户请将 `D:\papers` 替换为本机路径，例如 `/home/you/papers`。

**处理一个文件夹：**

```powershell
python extract_paper_metadata.py "D:\papers"
```

默认输出位置：

```text
outputs/paper_metadata.jsonl
```

**递归处理子文件夹：**

```powershell
python extract_paper_metadata.py "D:\papers" --recursive
```

**断点续跑，跳过已经成功处理的文件：**

```powershell
python extract_paper_metadata.py "D:\papers" --recursive --resume
```

**导出 CSV：**

```powershell
python extract_paper_metadata.py "D:\papers" --format csv -o outputs/paper_metadata.csv
```

**使用其他 API，从指定环境变量读取密钥：**

```powershell
python extract_paper_metadata.py "D:\papers" --base-url "https://api.example.com/v1" --model "your-model" --api-key-env OTHER_API_KEY
```

运行前，需要在环境变量或 `.env` 中设置 `OTHER_API_KEY`。

**接口不支持 `response_format` 时关闭 JSON 模式：**

```powershell
python extract_paper_metadata.py "D:\papers" --no-json-mode
```

**增加读取页数和文本长度：**

```powershell
python extract_paper_metadata.py "D:\papers" --max-pages 12 --max-chars 36000
```

**查看全部参数：**

```powershell
python extract_paper_metadata.py --help
```

默认请求超时为 90 秒，文件之间暂停 0.3 秒，可通过 `--timeout` 和 `--sleep` 调整。

### 输出字段

每条结果包含：

| 字段 | 含义 |
| --- | --- |
| `file` | 来源文件路径 |
| `status` | 处理状态：`ok` 或 `error` |
| `title` | 论文标题 |
| `authors` | 作者姓名 |
| `schools` | 学校、机构或其他所属单位 |
| `abstract` | 摘要原文 |
| `keywords` | 关键词 |
| `error` | 处理失败时的错误信息 |

作者、单位、关键词在 JSONL 中以列表保存，在 CSV 中以分号连接。

### 注意事项与限制

- JSONL 逐篇保存。`--resume` 按路径跳过已成功处理的文件，失败项重试后追加新记录。
- 续跑不会检测文件内容是否更新。修改过的论文建议使用新的输出文件重新处理。
- 不使用 `--resume` 时会覆盖指定的同名输出文件。
- CSV 在整个批次完成后保存，不支持断点续跑。
- 默认读取 PDF 前 8 页，每篇最多发送 24000 个字符。
- 扫描版 PDF 需要先进行 OCR，本工具不包含 OCR 功能。
- `status=ok` 表示获得了非空结果，不保证所有字段完整或准确，重要信息请对照原文核查。
- 提取的文本会发送至配置的 API，费用和数据处理方式取决于服务商，建议先用少量论文测试。
- 将不可信文档内容导入表格软件时，请按文本导入，避免被解释为公式。

### 开发检查

测试使用模拟响应，不调用付费 API：

```bash
python -m unittest discover -s tests -v
```
