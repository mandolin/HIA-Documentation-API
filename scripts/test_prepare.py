"""发布归档边界回归夹具。 Regression fixtures for publication archive boundaries."""

import gzip
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from prepare import digest, prepare, valid_path


class PublicationTests(unittest.TestCase):
    """通过小型工件核拒绝路径，不冒充真实 API 生成验收。 Check rejection paths with small artifacts without claiming API production coverage."""

    def setUp(self):
        """为每例创建独立归档和报告。 Create isolated archives and reports for every case."""
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)

    def fixture(self, missing=False, linked=False):
        """生成真实 TAR/GZIP 与逐文件摘要。 Build actual TAR/GZIP bytes and per-file digests."""
        files = {'index.html': b'<a href="zh-CN/">API</a>'}
        for locale in ('en', 'zh-CN'):
            index = {'contract': 'hia-project-navigation-index', 'contractVersion': '0.1.0-draft',
                     'project': {'id': 'project:hia-core-api-reference'}, 'entries': [
                         {'contentPath': 'entry.html', 'noScriptPagePath': 'entry.html', 'noScriptLocalePages': [{'path': 'entry.html'}]}]}
            files[locale + '/project-index.json'] = json.dumps(index).encode()
            files[locale + '/documentation-ui-locale-completeness.json'] = b'{"status":"complete"}'
            if not missing:
                files[locale + '/entry.html'] = b'<h1>Fixture</h1>'
        tar_path = self.root / 'site.tar'
        with tarfile.open(tar_path, 'w') as archive:
            for name, body in files.items():
                member = tarfile.TarInfo(name)
                member.size = len(body)
                if linked and name == 'index.html':
                    member.type = tarfile.SYMTYPE
                    member.linkname = '/outside'
                archive.addfile(member, io.BytesIO(body))
        packed = self.root / 'site.tar.gz'
        with tar_path.open('rb') as source, gzip.open(packed, 'wb') as target:
            target.write(source.read())
        report = {'sourceRepository': 'mandolin/HIA-Documentation', 'sourceCommit': 'a'*40,
                  'producerCommit': 'b'*40, 'packages': [f'fixture-{i}' for i in range(13)],
                  'files': len(files), 'bytes': sum(map(len, files.values())), 'inventory': []}
        import hashlib
        for name, body in files.items():
            report['inventory'].append({'path': name, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()})
        report_path = self.root / 'report.json'
        report_path.write_text(json.dumps(report), encoding='utf-8')
        snapshot = {'repository': report['sourceRepository'], 'commit': report['sourceCommit'],
                    'producerCommit': report['producerCommit'], 'files': report['files'], 'bytes': report['bytes'],
                    'tarBytes': tar_path.stat().st_size, 'tarSha256': digest(tar_path), 'gzipSha256': digest(packed),
                    'reportSha256': digest(report_path), 'entriesPerLocale': 1}
        return snapshot, packed, report_path, self.root / 'output'

    def test_valid_snapshot(self):
        """有效文件完整展开。 Extract every valid file."""
        args = self.fixture()
        prepare(*args)
        self.assertTrue((args[-1] / 'en/entry.html').is_file())

    def test_digest_mismatch(self):
        """更改归档摘要即拒绝。 Reject a changed archive digest."""
        args = self.fixture()
        args[0]['gzipSha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            prepare(*args)

    def test_missing_target(self):
        """逐文件摘要正确仍须有真实条目目标。 Require real entry targets even with valid file hashes."""
        with self.assertRaisesRegex(ValueError, 'Missing API entry target'):
            prepare(*self.fixture(missing=True))

    def test_symlink(self):
        """已固定摘要的链接归档仍拒绝。 Reject linked archive members even when pinned by digest."""
        with self.assertRaisesRegex(ValueError, 'archive member'):
            prepare(*self.fixture(linked=True))

    def test_source_mismatch(self):
        """报告来源必须与清单提交一致。 Require the report source to match the manifest revision."""
        args = self.fixture()
        args[0]['commit'] = 'c'*40
        with self.assertRaisesRegex(ValueError, 'source revisions'):
            prepare(*args)

    def test_paths(self):
        """越界、编码、隐藏和工程目录均拒绝。 Reject escaping, encoded, hidden and build-only paths."""
        for name in ('../x', '/x', 'en/../x', 'en/a%20b', 'en/.git/config', 'package-api/api.json', 'en\\x'):
            self.assertFalse(valid_path(name), name)


if __name__ == '__main__':
    unittest.main()
