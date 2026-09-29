"""File preparation and validated exports for an agent. No model or network client."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

from paper_documents import discover_files, extract_text

FIELDS = ('title', 'authors', 'schools', 'abstract', 'keywords')
LIST_FIELDS = ('authors', 'schools', 'keywords')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def prepare(source, work, recursive=False, max_pages=3, max_chars=12000):
    source = source.resolve()
    if not source.is_dir():
        raise ValueError('Input must be a folder')
    if max_pages <= 0 or max_chars <= 0:
        raise ValueError('Page and character limits must be positive')
    files = discover_files(source, recursive)
    if not files:
        raise ValueError('No supported documents found')
    # A new directory prevents accidental replacement of saved agent results.
    work.mkdir(parents=True, exist_ok=False)
    (work / 'texts').mkdir()
    (work / 'results').mkdir()
    records = []
    for number, path in enumerate(files, 1):
        item = {'id': f'{number:06d}', 'file': str(path), 'sha256': '', 'error': ''}
        try:
            item['sha256'] = digest(path)
            excerpt = extract_text(path, max_pages, max_chars + 1)
            item['truncated'] = len(excerpt) > max_chars
            (work / 'texts' / (item['id'] + '.txt')).write_text(excerpt[:max_chars], encoding='utf-8')
        except Exception as exc:
            item['error'] = str(exc)
        records.append(item)
    manifest = {'input': str(source), 'max_pages': max_pages, 'max_chars': max_chars, 'papers': records}
    write_json(work / 'manifest.json', manifest)
    return {'total': len(records), 'read_errors': sum(bool(x['error']) for x in records),
            'work_dir': str(work.resolve())}


def next_paper(work, batch_size=None, max_batch_chars=180000):
    if (batch_size is not None and batch_size <= 0) or max_batch_chars <= 0:
        raise ValueError('Batch limits must be positive')
    manifest = read_json(work / 'manifest.json')
    batch = []
    chars = 0
    longest = 0
    for item in manifest['papers']:
        if not item['error'] and not (work / 'results' / (item['id'] + '.json')).exists():
            text = (work / 'texts' / (item['id'] + '.txt')).read_text(encoding='utf-8')
            limit = batch_size if batch_size is not None else (
                20 if max(longest, len(text)) <= 6000 else 10)
            if batch and (len(batch) >= limit or chars + len(text) > max_batch_chars):
                break
            # Always include one complete prepared excerpt; never silently truncate it.
            batch.append({**item, 'max_pages': manifest['max_pages'], 'text': text})
            chars += len(text)
            longest = max(longest, len(text))
    return {'done': not batch, 'papers': batch, 'text_chars': chars,
            'total': len(manifest['papers']),
            'read_errors': sum(bool(x['error']) for x in manifest['papers'])}


def save_result(work, paper_id, metadata):
    manifest = read_json(work / 'manifest.json')
    item = next((x for x in manifest['papers'] if x['id'] == paper_id), None)
    if item is None or item['error']:
        raise ValueError('Unknown or unreadable paper ID')
    if digest(Path(item['file'])) != item['sha256']:
        raise ValueError('Source changed; prepare a new work directory')
    if not isinstance(metadata, dict) or set(metadata) != set(FIELDS):
        raise ValueError('Expected exactly: ' + ', '.join(FIELDS))
    for key in FIELDS:
        value = metadata[key]
        if key in LIST_FIELDS:
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                raise ValueError(key + ' must be a list of strings')
            metadata[key] = list(dict.fromkeys(x.strip() for x in value if x.strip()))
        elif not isinstance(value, str):
            raise ValueError(key + ' must be a string')
        else:
            metadata[key] = value.strip()
    missing = [key for key in FIELDS if not metadata[key]]
    result = {'file': item['file'], 'sha256': item['sha256'],
              'status': 'needs_review' if missing else 'ok', **metadata,
              'missing_fields': missing, 'error': ''}
    write_json(work / 'results' / (paper_id + '.json'), result)
    return {'id': paper_id, 'status': result['status'], 'missing_fields': missing}


def export_results(work, output, output_format):
    manifest = read_json(work / 'manifest.json')
    rows = []
    for item in manifest['papers']:
        result_path = work / 'results' / (item['id'] + '.json')
        if result_path.exists():
            row = read_json(result_path)
            if digest(Path(item['file'])) != item['sha256']:
                raise ValueError('Source changed: ' + item['file'])
        else:
            row = {'file': item['file'], 'sha256': item['sha256'],
                   'status': 'error' if item['error'] else 'pending',
                   **{key: [] if key in LIST_FIELDS else '' for key in FIELDS},
                   'missing_fields': list(FIELDS), 'error': item['error']}
        rows.append(row)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Never overwrite an existing export, manuscript, or task checkpoint.
    with output.open('x', encoding='utf-8-sig' if output_format == 'csv' else 'utf-8', newline='') as stream:
        if output_format == 'jsonl':
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        else:
            columns = ['file', 'status', *FIELDS, 'missing_fields', 'error', 'sha256']
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                values = {key: '; '.join(value) if isinstance(value, list) else value for key, value in row.items()}
                # Spreadsheet formula injection protection; JSONL retains originals.
                for key, value in values.items():
                    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
                        values[key] = "'" + value
                writer.writerow(values)
    return {'output': str(output.resolve()),
            'counts': {status: sum(x['status'] == status for x in rows)
                       for status in ('ok', 'needs_review', 'error', 'pending')}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare')
    prep.add_argument('input', type=Path)
    prep.add_argument('--work-dir', type=Path, required=True)
    prep.add_argument('--recursive', action='store_true')
    prep.add_argument('--max-pages', type=int, default=3)
    prep.add_argument('--max-chars', type=int, default=12000)
    nxt = commands.add_parser('next')
    nxt.add_argument('--work-dir', type=Path, required=True)
    nxt.add_argument('--batch-size', type=int,
                     help='Fixed paper limit; default: 10, expanded to 20 when every excerpt is <=6000 characters')
    nxt.add_argument('--max-batch-chars', type=int, default=180000)
    save = commands.add_parser('save')
    save.add_argument('--work-dir', type=Path, required=True)
    save.add_argument('--id', help='Single-paper mode; omit to save an array of {id, metadata}')
    save.add_argument('--metadata', type=Path, required=True)
    export = commands.add_parser('export')
    export.add_argument('--work-dir', type=Path, required=True)
    export.add_argument('--output', type=Path, required=True)
    export.add_argument('--format', choices=['jsonl', 'csv'], default='jsonl')
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            result = prepare(args.input, args.work_dir, args.recursive, args.max_pages, args.max_chars)
        elif args.command == 'next':
            result = next_paper(args.work_dir, args.batch_size, args.max_batch_chars)
        elif args.command == 'save':
            data = read_json(args.metadata)
            if args.id:
                result = save_result(args.work_dir, args.id, data)
            else:
                if not isinstance(data, list) or not data:
                    raise ValueError('Batch metadata must be a nonempty array of {id, metadata}')
                result = []
                for entry in data:
                    if not isinstance(entry, dict) or set(entry) != {'id', 'metadata'}:
                        raise ValueError('Each entry must contain id and metadata')
                    result.append(save_result(args.work_dir, entry['id'], entry['metadata']))
        else:
            result = export_results(args.work_dir, args.output, args.format)
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
