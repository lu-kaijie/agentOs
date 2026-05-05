# 整理前清单

本文记录本次文档与 tag 治理开始前的仓库现状，用于说明为什么需要这次 change。

## 文档现状

整理前主要文档分布：

- `README.md`
  - 同时承载产品介绍、快速使用、开发说明、历史里程碑和学习路径
- `docs/product-usage.md`
- `docs/product-verification-checklist.md`
- `docs/release-checklist.md`
- `docs/second-change-milestones.md`
- `docs/third-change-milestones.md`
- `docs/milestones/v0.22.0.md` 到 `docs/milestones/v0.27.0.md`

问题：

- `README.md` 过载
- `docs/` 根目录既有产品文档，也有阶段性学习文档
- 同一个主题往往在多个文件里重复出现
- milestone 说明、版本历史和产品使用文档没有统一入口

## Tag 现状

整理前发现的主要问题：

- `v0.4.0` 与 `v0.5.0` 指向同一个 commit
- `v0.13.0` 与 `v0.14.0` 指向同一个 commit
- `v0.18.0` 与 `v0.19.0` 指向同一个 commit
- `v0.21.0` 与 `v0.22.0` 指向同一个 commit
- `v0.23.0` 与 `v0.24.0` 指向同一个 commit
- `v0.28.0` 缺失

此外还有一类问题：

- 某些未打 tag 的中间 commit 实际对应了明确里程碑
- 部分旧文档里的 tag 说明与 git 实际指向不一致

## 本次整理目标

- 形成一份规范的 tag 与里程碑映射表
- 重建文档结构，按用途分区
- 让 `README.md` 回到首页职责
- 完成两轮核对，避免改完后再次错位
