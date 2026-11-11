"""核验固定核心 API 发布工件并原子展开。 Verify and atomically unpack a pinned core API release."""

import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile
import tempfile


def require(condition, message):
    """检查发布不变量，失败停止。 Enforce publication invariants and stop on failure."""
    if not condition:
        raise ValueError(message)


def digest(file):
    """流式计算文件摘要。 Compute a file digest with bounded memory."""
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def valid_path(name):
    """只接受两语言和根入口的普通相对路径。 Accept ordinary relative paths under both locales and root entries."""
    route = PurePosixPath(name)
    return (name == route.as_posix() and not route.is_absolute()
            and '..' not in route.parts and not any(char in name for char in '\\:%?#')
            and all(not part.startswith('.') or name in ('.nojekyll', 'en/.gitattributes', 'zh-CN/.gitattributes') for part in route.parts)
            and route.parts[0] in ('en', 'zh-CN', 'index.html', '.nojekyll'))


def check_site(site, expected_entries, resources=()):
    """核验双语索引与所有条目目标，禁止遗漏原生地图。 Check bilingual indexes and every entry target, retaining native maps."""
    for locale in ('en', 'zh-CN'):
        root = site / locale
        index = json.loads((root / 'project-index.json').read_text(encoding='utf-8'))
        require(index['contract'] == 'hia-project-navigation-index'
                and index['contractVersion'] == '0.1.0-draft'
                and index['project']['id'] == 'project:hia-core-api-reference', 'Unexpected API index identity.')
        require(len(index['entries']) == expected_entries, 'Incomplete API index.')
        for entry in index['entries']:
            targets = [entry['contentPath'], entry['noScriptPagePath'], *[page['path'] for page in entry['noScriptLocalePages']]]
            if entry.get('docSourceMap'):
                targets.append(entry['docSourceMap']['path'])
            for target in targets:
                route = target.split('#')[0]
                require(valid_path(locale + '/' + route) and (root / route).is_file(), 'Missing API entry target.')
        report = json.loads((root / 'documentation-ui-locale-completeness.json').read_text(encoding='utf-8'))
        require(report['status'] == 'complete', 'Incomplete interface messages.')
        for resource in resources:
            # <lang zh-CN>资源声明单独核对，完整模块总数不能掩盖资源遗漏。</lang><lang en>Check resource declarations independently so module totals cannot conceal missing resource values.</lang>
            entries = [entry for entry in index['entries']
                       if entry.get('input', {}).get('path') == resource['prefix'] + '/resource-001.hia.json']
            require(len(entries) == resource['values'], 'Incomplete resource value coverage.')
            snapshot = resource['prefix'] + '/resource-001.source.json'
            require(valid_path(locale + '/' + snapshot)
                    and (root / snapshot).is_file()
                    and digest(root / snapshot) == resource['sha256'], 'Unexpected resource source snapshot.')
            for entry in entries:
                source = entry.get('source', {})
                require(source.get('path') == resource['source'], 'Unexpected resource source identity.')
                for key in ('fetchUrl', 'linkUrl'):
                    target = source.get(key, '').split('#')[0]
                    require(target and valid_path(locale + '/' + target)
                            and (root / target).is_file(), 'Missing resource source target.')


def prepare(snapshot, archive, report_path, output):
    """先核归档、逐文件摘要与来源，再将独占暂存目录改名。 Verify archive, file hashes and revisions before renaming an exclusive stage."""
    require(not output.exists() and not output.is_symlink(), 'Output already exists.')
    require(snapshot['tarBytes'] <= 2 * 1024**3 and snapshot['bytes'] <= 1_000_000_000
            and snapshot['files'] <= 100_000, 'Snapshot exceeds the publication budget.')
    require(digest(archive) == snapshot['gzipSha256'], 'Compressed snapshot digest mismatch.')
    require(digest(report_path) == snapshot['reportSha256'], 'Build report digest mismatch.')
    report = json.loads(report_path.read_text(encoding='utf-8'))
    require(report['sourceRepository'] == snapshot['repository']
            and report['sourceCommit'] == snapshot['commit']
            and report['producerCommit'] == snapshot['producerCommit'], 'Unexpected source revisions.')
    require(len(report['packages']) == 13 and len(set(report['packages'])) == 13, 'Unexpected package scope.')
    # <lang zh-CN>旧模块归档省略资源字段；新版清单显式固定资源范围与逐语言值数。</lang><lang en>Legacy module archives omit resource fields; newer manifests explicitly pin resource scope and per-locale value counts.</lang>
    resources = report.get('resources', [])
    require(report.get('resourcePackages', []) == snapshot.get('resourcePackages', [])
            and len(resources) == snapshot.get('resourceEntries', 0)
            and sum(row['values'] for row in resources) == snapshot.get('resourceValuesPerLocale', 0)
            and set(row['package'] for row in resources) == set(report.get('resourcePackages', [])),
            'Unexpected resource scope.')
    if resources:
        require(sorted(report.get('sourcePolicy', {}).get('paths', []))
                == sorted(row['source'] for row in resources), 'Unexpected resource source policy.')
    expected = {item['path']: item for item in report['inventory']}
    require(len(expected) == len(report['inventory']) == snapshot['files'] == report['files']
            and report['bytes'] == snapshot['bytes'], 'Unexpected report inventory.')
    with tempfile.TemporaryDirectory(dir=output.parent) as scratch:
        tar_path = Path(scratch) / 'verified.tar'
        with gzip.open(archive, 'rb') as source, tar_path.open('wb') as destination:
            remaining = snapshot['tarBytes']
            while remaining:
                block = source.read(min(remaining, 1024**2))
                require(block, 'Truncated snapshot.')
                destination.write(block)
                remaining -= len(block)
            require(not source.read(1), 'Expanded snapshot exceeds its declared size.')
        require(digest(tar_path) == snapshot['tarSha256'], 'Snapshot TAR digest mismatch.')
        stage = Path(scratch) / 'site'
        stage.mkdir()
        seen = set()
        total = 0
        with tarfile.open(tar_path, 'r:') as bundle:
            for member in bundle:
                name = member.name
                require(valid_path(name) and member.isfile() and name not in seen, 'Invalid or duplicate archive member.')
                require(name in expected and member.size == expected[name]['bytes']
                        and member.size <= 32 * 1024**2, 'Unexpected archive file.')
                # <lang zh-CN>逐文件提取正文，归档权限、符号链接与硬链接均不会进入输出。</lang><lang en>Extract file bodies individually so archive permissions, symbolic links and hard links never enter the output.</lang>
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source, target.open('xb') as destination:
                    shutil.copyfileobj(source, destination)
                require(digest(target) == expected[name]['sha256'], 'Published file digest mismatch.')
                if name in ('en/.gitattributes', 'zh-CN/.gitattributes'):
                    require(target.read_bytes() == b'sources/*.txt -text\n', 'Unexpected source attributes.')
                seen.add(name)
                total += member.size
        require(seen == expected.keys() and total == snapshot['bytes'], 'Incomplete snapshot.')
        check_site(stage, snapshot['entriesPerLocale'], resources)
        stage.rename(output)
    print(f'Validated {len(seen)} files and {total} bytes at {snapshot["commit"]}.')


if __name__ == '__main__':
    manifest, archive_path, report, output_path = map(Path, sys.argv[1:])
    prepare(json.loads(manifest.read_text(encoding='utf-8')), archive_path, report, output_path)
