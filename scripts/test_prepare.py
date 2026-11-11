"""发布归档边界回归夹具。 Regression fixtures for publication archive boundaries."""

import gzip
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from prepare import digest, prepare, valid_path, check_site


class PublicationTests(unittest.TestCase):
    """通过小型工件核拒绝路径，不冒充真实 API 生成验收。 Check rejection paths with small artifacts without claiming API production coverage."""

    def setUp(self):
        """为每例创建独立归档和报告。 Create isolated archives and reports for every case."""
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)

    def fixture(self, missing=False, linked=False, attributes=None):
        """生成真实 TAR/GZIP 与逐文件摘要。 Build actual TAR/GZIP bytes and per-file digests."""
        files = {'index.html': b'<a href="zh-CN/">API</a>'}
        if attributes is not None:
            files['en/.gitattributes'] = attributes
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

    def test_resource_scope_mismatch(self):
        """资源选择必须由固定发布清单明确记录。 Require resource selection in the pinned publication manifest."""
        args = self.fixture()
        report = json.loads(args[2].read_text(encoding='utf-8'))
        report['resourcePackages'] = ['@hia-doc/plugin-sdk']
        args[2].write_text(json.dumps(report), encoding='utf-8')
        args[0]['reportSha256'] = digest(args[2])
        with self.assertRaisesRegex(ValueError, 'resource scope'):
            prepare(*args)

    def test_resource_source_policy_mismatch(self):
        """资源范围正确仍须核精确来源策略。 Check exact source policy even when resource scope matches."""
        args = self.fixture()
        report = json.loads(args[2].read_text(encoding='utf-8'))
        report['resourcePackages'] = ['@hia-doc/plugin-sdk']
        report['resources'] = [{'package': '@hia-doc/plugin-sdk', 'source': 'reviewed.json', 'values': 1}]
        report['sourcePolicy'] = {'paths': ['different.json']}
        args[2].write_text(json.dumps(report), encoding='utf-8')
        args[0].update({
            'reportSha256': digest(args[2]),
            'resourcePackages': report['resourcePackages'],
            'resourceEntries': 1,
            'resourceValuesPerLocale': 1,
        })
        with self.assertRaisesRegex(ValueError, 'resource source policy'):
            prepare(*args)

    def test_paths(self):
        """越界、编码、隐藏和工程目录均拒绝。 Reject escaping, encoded, hidden and build-only paths."""
        for name in ('../x', '/x', 'en/../x', 'en/a%20b', 'en/.git/config', 'package-api/api.json', 'en\\x'):
            self.assertFalse(valid_path(name), name)

    def test_source_attributes(self):
        """保留渲染器固定的源码字节保护元数据。 Retain the renderer's fixed source-byte protection metadata."""
        prepare(*self.fixture(attributes=b'sources/*.txt -text\n'))

    def test_changed_source_attributes(self):
        """拒绝其它Git属性内容。 Reject other Git attribute contents."""
        with self.assertRaisesRegex(ValueError, 'source attributes'):
            prepare(*self.fixture(attributes=b'* text\n'))


class ResourceSiteTests(unittest.TestCase):
    """逐值采用和源码地址的发布回归。 Publication regressions for per-value adoption and source targets."""

    def setUp(self):
        """准备双语最小资源工件。 Prepare a minimal bilingual resource artifact."""
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.resource = {
            'prefix': 'package-resources/sdk/schema.json',
            'source': 'packages/plugin-sdk/dist/schema.json',
            'values': 1,
        }
        for locale in ('en', 'zh-CN'):
            root = self.root / locale
            snapshot = root / self.resource['prefix'] / 'resource-001.source.json'
            snapshot.parent.mkdir(parents=True)
            snapshot.write_bytes(b'{}')
            self.resource['sha256'] = digest(snapshot)
            entry = {
                'contentPath': 'entry.html',
                'noScriptPagePath': 'entry.html',
                'noScriptLocalePages': [{'path': 'entry.html'}],
                'input': {'path': self.resource['prefix'] + '/resource-001.hia.json'},
                'source': {
                    'path': self.resource['source'],
                    'fetchUrl': 'sources/schema.txt',
                    'linkUrl': 'sources/schema.html#L1',
                },
            }
            index = {
                'contract': 'hia-project-navigation-index',
                'contractVersion': '0.1.0-draft',
                'project': {'id': 'project:hia-core-api-reference'},
                'entries': [entry],
            }
            (root / 'project-index.json').write_text(json.dumps(index), encoding='utf-8')
            (root / 'documentation-ui-locale-completeness.json').write_text('{"status":"complete"}', encoding='utf-8')
            (root / 'entry.html').write_text('<h1>Resource</h1>', encoding='utf-8')
            (root / 'sources').mkdir()
            (root / 'sources/schema.txt').write_bytes(b'{}')
            (root / 'sources/schema.html').write_text('<pre id="L1">{}</pre>', encoding='utf-8')

    def test_valid_resource_site(self):
        """资源值与源码页完整可用。 Resource values and source pages are complete."""
        check_site(self.root, 1, [self.resource])

    def test_missing_value_coverage(self):
        """总条目数相同仍拒绝资源值缺项。 Reject missing resource values even with matching total entries."""
        self.resource['values'] = 2
        with self.assertRaisesRegex(ValueError, 'resource value'):
            check_site(self.root, 1, [self.resource])

    def test_changed_source_snapshot(self):
        """拒绝与报告摘要不符的原文。 Reject source bytes that disagree with the report."""
        target = self.root / 'en' / self.resource['prefix'] / 'resource-001.source.json'
        target.write_bytes(b'{"changed":true}')
        with self.assertRaisesRegex(ValueError, 'source snapshot'):
            check_site(self.root, 1, [self.resource])

    def test_missing_source_page(self):
        """静态源码链接必须存在实际目标。 Require an actual target for a static source link."""
        (self.root / 'en/sources/schema.html').unlink()
        with self.assertRaisesRegex(ValueError, 'resource source target'):
            check_site(self.root, 1, [self.resource])


if __name__ == '__main__':
    unittest.main()
