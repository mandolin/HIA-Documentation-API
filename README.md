# HIA Documentation System API Reference

Browse the HIA-generated [Chinese API reference](https://mandolin.github.io/HIA-Documentation-API/zh-CN/) or [English API reference](https://mandolin.github.io/HIA-Documentation-API/en/).

This site provides module documentation from thirteen core HIA packages. HIA generates signatures, fields, localization and native source maps from their actual public declarations. Resource entries, command entries and satellite packages have separate adoption inventories. Source-text reading follows explicit authorization, and missing source text remains an explicit state.

## Reproduce and publish

Build the [main repository](https://github.com/mandolin/HIA-Documentation) and its adjacent [TypeScript producer](https://github.com/mandolin/hia-tsdoc), then run `pnpm reference:core:build` in the main repository. Publish only the resulting `dist/core-api-reference/site/` directory. Its adjacent `build-report.json` records the exact source revisions and hashes of every runtime file.

This repository's `snapshot.json` pins a release archive, source revisions, file totals and digests. The manually dispatched Pages workflow downloads that archive and its build report, verifies every ordinary file, both language indexes and their direct targets, then deploys the checked site. A failed validation leaves the previous Pages deployment available.

The pinned archive includes an empty `.nojekyll` marker. GitHub's Pages upload action excludes dotfiles, so the uploaded site contains one fewer file with identical content bytes. All documentation, maps, indexes and theme assets are retained. [Upload action packaging](https://github.com/actions/upload-pages-artifact/blob/v4/action.yml).

To update the site, build from committed sources, archive only the files listed in the report, attach the archive and report to a uniquely named `core-api-<source-sha>` release, update `snapshot.json`, and dispatch **Core API Reference Pages**. To roll back, restore the earlier snapshot manifest and dispatch the workflow. Preserve release assets referenced by manifests.

## Scope and versions

The current documentation is a preview of the first formal system release. Package versions, source commits and artifact-contract versions remain distinct identities. Existing reference routes in the main repository and the [legacy reference site](https://mandolin.github.io/HIA-Documentation-Legacy/) remain independently available.

中文。本站是 HIA 自身生成的十三核心包模块参考，提供中英文入口、完整原生工件与静态条目。构建副本与来源报告独立保存，源码正文权限单独核验。发布清单固定工件及来源提交，工作流逐文件核验后部署。系统文档当前仍为正式初版预览。

## License

MIT. See [LICENSE](LICENSE).
