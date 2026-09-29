import csv
import json
import tempfile
import unittest
from pathlib import Path

from docx import Document
import paper_local as local


class LocalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'papers'
        self.source.mkdir()
        self.work = self.root / 'task'

    def paper(self, name='paper.docx', text='A title\nAuthor\nAbstract: original text'):
        document = Document()
        document.add_paragraph(text)
        path = self.source / name
        document.save(path)
        return path

    def metadata(self):
        return dict(title='A title', authors=['Author'], schools=['University'],
                    abstract='original text', keywords=['word'])

    def test_batch_resume_export_real_docx(self):
        for i in range(6):
            self.paper(f'{i}.docx')
        local.prepare(self.source, self.work)
        batch = local.next_paper(self.work, batch_size=5)
        self.assertEqual(len(batch['papers']), 5)
        self.assertIn('Abstract: original text', batch['papers'][0]['text'])
        for paper in batch['papers']:
            local.save_result(self.work, paper['id'], self.metadata())
        remaining = local.next_paper(self.work)
        self.assertEqual(len(remaining['papers']), 1)
        local.save_result(self.work, remaining['papers'][0]['id'], self.metadata())
        self.assertTrue(local.next_paper(self.work)['done'])
        output = self.root / 'results.jsonl'
        self.assertEqual(local.export_results(self.work, output, 'jsonl')['counts']['ok'], 6)
        self.assertEqual(len(output.read_text(encoding='utf-8').splitlines()), 6)
        with self.assertRaises(FileExistsError):
            local.export_results(self.work, output, 'jsonl')

    def test_budget_and_pending_and_errors(self):
        self.paper('a.docx')
        self.paper('b.docx')
        (self.source / 'broken.pdf').write_bytes(b'not a pdf')
        local.prepare(self.source, self.work)
        batch = local.next_paper(self.work, max_batch_chars=1)
        self.assertEqual(len(batch['papers']), 1)
        counts = local.export_results(self.work, self.root / 'partial.jsonl', 'jsonl')['counts']
        self.assertEqual(counts['pending'], 2)
        self.assertEqual(counts['error'], 1)

    def test_adaptive_batch_limits(self):
        # Minimal prepared text fixtures isolate grouping from document parsing.
        self.work.mkdir()
        (self.work / 'texts').mkdir()
        (self.work / 'results').mkdir()
        papers = []
        for i in range(25):
            paper_id = f'{i:06d}'
            papers.append({'id': paper_id, 'error': ''})
            (self.work / 'texts' / (paper_id + '.txt')).write_text('x' * 6000)
        local.write_json(self.work / 'manifest.json', {'papers': papers, 'max_pages': 3})
        self.assertEqual(len(local.next_paper(self.work)['papers']), 20)
        self.assertEqual(len(local.next_paper(self.work, batch_size=15)['papers']), 15)
        self.assertEqual(len(local.next_paper(self.work, max_batch_chars=18000)['papers']), 3)
        (self.work / 'texts' / '000000.txt').write_text('x' * 6001)
        self.assertEqual(len(local.next_paper(self.work)['papers']), 10)
        (self.work / 'texts' / '000000.txt').write_text('x' * 6000)
        (self.work / 'texts' / '000010.txt').write_text('x' * 6001)
        self.assertEqual(len(local.next_paper(self.work)['papers']), 10)

    def test_missing_fields_and_csv_protection(self):
        self.paper()
        local.prepare(self.source, self.work)
        data = self.metadata()
        data.update(title='=SUM(1,2)', schools=[])
        saved = local.save_result(self.work, '000001', data)
        self.assertEqual(saved['status'], 'needs_review')
        output = self.root / 'results.csv'
        local.export_results(self.work, output, 'csv')
        with output.open(encoding='utf-8-sig', newline='') as stream:
            row = next(csv.DictReader(stream))
        self.assertEqual(row['title'], "'=SUM(1,2)")

    def test_changed_source_and_bad_schema(self):
        paper = self.paper()
        local.prepare(self.source, self.work)
        with self.assertRaises(ValueError):
            local.save_result(self.work, '../escape', self.metadata())
        with self.assertRaises(ValueError):
            local.save_result(self.work, '000001', {'title': 'incomplete schema'})
        paper.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            local.save_result(self.work, '000001', self.metadata())
        self.assertFalse((self.work / 'results' / '000001.json').exists())


if __name__ == '__main__':
    unittest.main()
