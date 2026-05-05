# 整理核对记录

本文记录本次 `clean-up-tags-and-reorganize-docs` 的两轮核对结果。

## 第一轮核对：tag 映射

核对目标：

- 每个 tag 是否指向规划好的 commit
- 是否补齐缺失 tag
- 是否消除错误重复指向

核对方式：

- `git tag --sort=version:refname`
- `git rev-list -n 1 <tag>`
- 对照 [tag-and-milestone-map.md](tag-and-milestone-map.md)

结果：

- `v0.1.0` 到 `v0.29.0` 当前已经连续存在
- `v0.5.0`、`v0.6.0`、`v0.12.0`、`v0.14.0`、`v0.19.0`、`v0.22.0`、`v0.24.0`、`v0.25.0` 已重新对齐
- `v0.28.0` 已补齐
- 通过 `git log --decorate --graph` 复核后，tag 序列已与目标映射表一致

## 第二轮核对：文档一致性

核对目标：

- `README.md` 是否只承担首页职责
- `docs/product`、`docs/roadmap`、`docs/learn`、`docs/architecture`、`docs/interview` 是否齐全
- 文档链接是否存在
- 版本记录是否与实际 tag 一致

核对方式：

- 检查 README 链接
- 检查目录结构
- 对照 release history 与 tag map

结果：

- `README.md` 已回收为首页与导航页
- `docs/product`、`docs/roadmap`、`docs/learn`、`docs/architecture`、`docs/interview` 已建立
- 原 `docs/` 根目录中的旧重复文档已迁移或删除
- milestone 文档已统一迁移到 `docs/roadmap/milestones/`
- 通过 `find docs -maxdepth 3 -type f` 与 README 链接人工核对后，主文档入口已对齐
