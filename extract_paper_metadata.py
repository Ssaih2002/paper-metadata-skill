import argparse
import csv
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
from dotenv import load_dotenv
from tqdm import tqdm
from paper_documents import discover_files, extract_text


DEFAULT_BASE_URL = "https://api.deepseek.com"
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc"}


SYSTEM_PROMPT = """你是论文信息抽取助手。请从用户提供的论文正文片段中抽取元数据。
只返回 JSON，不要返回 Markdown、解释或多余文字。

JSON 字段固定为：
{
  "title": "论文标题，无法确定则为空字符串",
  "authors": ["作者姓名1", "作者姓名2"],
  "schools": ["学校或单位名称1", "学校或单位名称2"],
  "abstract": "论文摘要原文，不要改写或自行总结，无法确定则为空字符串",
  "keywords": ["关键词1", "关键词2"]
}

要求：
1. 不要编造正文中没有的信息。
2. 作者姓名只保留姓名，不要附带学号、邮箱、脚注。
3. schools 字段优先提取学校，其次提取学院、单位或机构。
4. 摘要和关键词优先识别中文的“摘要”“关键词”，也兼容 Abstract、Keywords。
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="批量读取论文 PDF/Word 文档，通过 OpenAI 兼容 API 提取元数据。"
    )
    parser.add_argument("input_dir", help="论文文件夹路径")
    parser.add_argument(
        "-o",
        "--output",
        default="outputs/paper_metadata.jsonl",
        help="输出文件路径，默认 outputs/paper_metadata.jsonl",
    )
    parser.add_argument(
        "--format",
        choices=["jsonl", "csv"],
        default="jsonl",
        help="输出格式，默认 jsonl",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="递归读取子文件夹",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL") or os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        help="模型名，读取 LLM_MODEL，兼容 DEEPSEEK_MODEL",
    )
    parser.add_argument("--base-url", default=os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL),
                        help="OpenAI 兼容 API 基础地址，例如 https://api.example.com/v1")
    parser.add_argument("--api-key-env", default="LLM_API_KEY",
                        help="存放密钥的环境变量名，默认 LLM_API_KEY，兼容 DEEPSEEK_API_KEY")
    parser.add_argument("--no-json-mode", action="store_true",
                        help="接口不支持 response_format 时关闭 JSON 模式")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=8,
        help="每个 PDF 最多读取前多少页，默认 8",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=24000,
        help="每篇论文最多发送给 AI 的字符数，默认 24000",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.3,
        help="每次调用 DeepSeek 后暂停秒数，避免触发限速，默认 0.3",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="API 请求超时时间，默认 90 秒",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="跳过输出文件里已成功处理过的文件",
    )
    return parser.parse_args()


def call_llm(
    api_key: str,
    model: str,
    text: str,
    timeout: int,
    base_url: str = DEFAULT_BASE_URL,
    json_mode: bool = True,
    retries: int = 3,
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请抽取以下论文片段中的元数据：\n\n{text}"},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    if not json_mode:
        payload.pop("response_format")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(
                base_url.rstrip("/") + "/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return normalize_result(parse_json_content(content))
        except Exception as exc:
            last_error = exc
            if isinstance(exc, requests.HTTPError) and exc.response is not None:
                code = exc.response.status_code
                if 400 <= code < 500 and code not in (408, 429):
                    break
            if attempt < retries:
                time.sleep(2 * attempt)

    raise RuntimeError(f"API 调用失败：{last_error}")


def parse_json_content(content: str) -> Dict[str, Any]:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content).strip()
        content = re.sub(r"```$", "", content).strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.S)
        if not match:
            raise
        data = json.loads(match.group(0))

    if not isinstance(data, dict):
        raise ValueError("模型返回的 JSON 不是对象")
    return data


def normalize_result(data: Dict[str, Any]) -> Dict[str, Any]:
    result = {
        "title": as_string(data.get("title")),
        "authors": as_string_list(data.get("authors")),
        "schools": as_string_list(data.get("schools")),
        "abstract": as_string(data.get("abstract")),
        "keywords": as_string_list(data.get("keywords")),
    }
    if not any(result.values()):
        raise ValueError("模型没有返回有效的论文信息")
    return result


def as_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def as_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        values = value
    elif isinstance(value, str):
        values = re.split(r"[；;，,\n]+", value)
    else:
        values = [value]

    result = []
    for item in values:
        text = as_string(item)
        if text and text not in result:
            result.append(text)
    return result


def load_done_files(output_path: Path) -> set[str]:
    if not output_path.exists() or output_path.suffix.lower() != ".jsonl":
        return set()

    done = set()
    with output_path.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("status") == "ok" and row.get("file"):
                done.add(str(row["file"]))
    return done


def write_jsonl(output_path: Path, rows: Iterable[Dict[str, Any]], append: bool) -> None:
    mode = "a" if append else "w"
    with output_path.open(mode, encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
            file.flush()


def write_csv(output_path: Path, rows: List[Dict[str, Any]]) -> None:
    fieldnames = [
        "file",
        "status",
        "title",
        "authors",
        "schools",
        "abstract",
        "keywords",
        "error",
    ]
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            csv_row = row.copy()
            for key in ("authors", "schools", "keywords"):
                value = csv_row.get(key, [])
                csv_row[key] = "；".join(value) if isinstance(value, list) else value
            writer.writerow({key: csv_row.get(key, "") for key in fieldnames})


def process_file(
    path: Path,
    api_key: str,
    model: str,
    max_pages: int,
    max_chars: int,
    timeout: int,
    base_url: str = DEFAULT_BASE_URL,
    json_mode: bool = True,
) -> Dict[str, Any]:
    base = {"file": str(path), "status": "ok"}
    try:
        text = extract_text(path, max_pages=max_pages, max_chars=max_chars)
        metadata = call_llm(api_key, model, text, timeout=timeout,
                            base_url=base_url, json_mode=json_mode)
        return {**base, **metadata, "error": ""}
    except Exception as exc:
        return {
            **base,
            "status": "error",
            "title": "",
            "authors": [],
            "schools": [],
            "abstract": "",
            "keywords": [],
            "error": str(exc),
        }


def main() -> None:
    load_dotenv()
    args = parse_args()
    api_key = os.getenv(args.api_key_env)
    if not api_key and args.api_key_env == "LLM_API_KEY":
        api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit(f"请先设置 {args.api_key_env}，或在 .env 文件中填写。")
    if min(args.max_pages, args.max_chars, args.timeout) <= 0 or args.sleep < 0:
        raise SystemExit("页数、字符数、超时必须大于 0，暂停秒数不能为负数。")
    if args.resume and (args.format != "jsonl" or Path(args.output).suffix.lower() != ".jsonl"):
        raise SystemExit("续跑仅支持 .jsonl 输出，请使用 --format jsonl 和 .jsonl 输出路径。")

    input_dir = Path(args.input_dir)
    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"输入路径不是文件夹：{input_dir}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    files = discover_files(input_dir, recursive=args.recursive)
    if not files:
        raise SystemExit("没有找到 .pdf、.docx 或 .doc 文件。")

    append_jsonl = args.format == "jsonl" and args.resume and output_path.exists()
    done_files = load_done_files(output_path) if args.resume else set()
    pending_files = [path for path in files if str(path) not in done_files]

    rows: List[Dict[str, Any]] = []
    if args.format == "jsonl":
        for path in tqdm(pending_files, desc="处理论文"):
            row = process_file(
                path,
                api_key=api_key,
                model=args.model,
                max_pages=args.max_pages,
                max_chars=args.max_chars,
                timeout=args.timeout,
                base_url=args.base_url,
                json_mode=not args.no_json_mode,
            )
            write_jsonl(output_path, [row], append=True if append_jsonl or rows else False)
            rows.append(row)
            time.sleep(args.sleep)
    else:
        for path in tqdm(pending_files, desc="处理论文"):
            rows.append(
                process_file(
                    path,
                    api_key=api_key,
                    model=args.model,
                    max_pages=args.max_pages,
                    max_chars=args.max_chars,
                    timeout=args.timeout,
                    base_url=args.base_url,
                    json_mode=not args.no_json_mode,
                )
            )
            time.sleep(args.sleep)
        write_csv(output_path, rows)

    ok_count = sum(1 for row in rows if row["status"] == "ok")
    error_count = sum(1 for row in rows if row["status"] == "error")
    print(f"完成：本次处理 {len(rows)} 个文件，成功 {ok_count} 个，失败 {error_count} 个。")
    print(f"结果已保存到：{output_path}")


if __name__ == "__main__":
    main()
