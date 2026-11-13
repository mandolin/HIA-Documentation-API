# HIA Documentation System API Reference

Browse the HIA-generated [Chinese API reference](https://mandolin.github.io/HIA-Documentation-API/zh-CN/) or [English API reference](https://mandolin.github.io/HIA-Documentation-API/en/).

This site provides module documentation from thirteen core HIA packages and the two public plugin SDK JSON resources. HIA generates signatures, fields, localization and native source maps from their actual public declarations. Further resources, command entries and satellite packages have separate adoption inventories. Source-text reading follows explicit authorization, and missing source text remains an explicit state.

The JSON resources retain 526 original values, 59 lexical reference occurrences, full snapshots and exact source maps through JSONdoc. Source previews are limited to the two reviewed distribution files, with a 400-line window and separate complete declaration ranges. Resource content uses locale `und`; interface language remains independently selectable.

## Reproduce and publish

Build the [main repository](https://github.com/mandolin/HIA-Documentation) and its adjacent [TypeScript producer](https://github.com/mandolin/hia-tsdoc), then run `pnpm reference:core:build` in the main repository. Publish only the resulting `dist/core-api-reference/site/` directory. Its adjacent `build-report.json` records the exact source revisions and hashes of every runtime file.

This repository's `snapshot.json` pins a release archive, source revisions, file totals and digests. The manually dispatched Pages workflow downloads that archive and its build report, verifies every ordinary file, both language indexes and their direct targets, then deploys the checked site. A failed validation leaves the previous Pages deployment available.

The pinned archive includes an empty `.nojekyll` marker and, when source assets are present, fixed locale-root `.gitattributes` files protecting source-text bytes in Git. GitHub's Pages upload action excludes dotfiles. The uploaded site retains every documentation page, map, index, source and theme asset byte; packaging metadata exclusions are counted separately. [Upload action packaging](https://github.com/actions/upload-pages-artifact/blob/v4/action.yml).

To update the site, build from committed sources, archive only the files listed in the report, attach the archive and report to a uniquely named `core-api-<source-sha>` release, update `snapshot.json`, and dispatch **Core API Reference Pages**. To roll back, restore the earlier snapshot manifest and dispatch the workflow. Preserve release assets referenced by manifests.

## Scope and versions

The current documentation is a preview of the first formal system release. Package versions, source commits and artifact-contract versions remain distinct identities. Existing reference routes in the main repository and the [legacy reference site](https://mandolin.github.io/HIA-Documentation-Legacy/) remain independently available.

中文。本站由 HIA 自身生成十三核心包模块与插件SDK两份JSON资源参考，提供中英文界面、完整原生工件与静态条目。JSON资源保留526值和精确来源，正文语言为und。构建副本与来源报告独立保存，源码正文权限单独核验。发布清单固定工件及来源提交，工作流逐文件核验后部署。系统文档当前仍为正式初版预览。

## Command reference

The generated reference includes `hia`, including both command groups, all eleven leaf operations and their parameters. It provides localized usage, package and version identities, defaults, examples, exit results, static pages and authorized declaration-source links. Native descriptions, parser observations and original HIA documents remain available under `commands/` beside the independent website projection. Source positions are declaration-line anchors.

中文。本站增加主命令hia、两组、十一叶操作及参数，保留双语说明、包与版本身份、默认规则、示例、退出结果、无脚本页面及授权源码。commands目录独立保存原生描述、解析观察、原文档和网页投影，源码位置按声明行锚点解释。

## License

MIT. See [LICENSE](LICENSE).
