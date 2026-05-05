## Why

当前仓库已经完成了主要产品能力，但发布记录和文档体系没有同步收口：一方面，部分历史 tag 指向重复、缺失或与实际里程碑不一致；另一方面，README 和 `docs/` 同时承载产品介绍、使用说明、迭代记录、学习路径和源码讲解，结构混杂，后续维护成本高，也不利于把项目作为完整产品和完整工程案例对外展示。

现在需要做一次收尾治理，把“版本历史”与“文档体系”同时整理干净。这样既能让仓库对当前单用户维护场景更可控，也能让后续继续迭代时有稳定的信息入口、稳定的发布映射和稳定的学习/面试材料。

## What Changes

- 清点并修复历史 tag 与 milestone/commit 的映射关系，补齐缺失版本并消除重复指向。
- 建立统一的版本记录文档，明确每个版本、对应 change 阶段、主要能力和体验入口。
- 重写 `README.md`，把它收敛为项目首页与导航入口，而不是继续承担全部细节说明。
- 重组 `docs/` 目录，拆分为产品、路线图、学习、架构、面试等文档域。
- 新增中文文档，覆盖产品介绍、快速上手、迭代记录、一步一步构建过程、源码带读、面试知识点等内容。
- 清理或迁移现有零散文档，避免多个文件重复讲同一件事但版本不一致。

## Capabilities

### New Capabilities
- `release-governance-and-tag-history`: 定义版本 tag、里程碑映射、发布记录和治理规则，保证仓库版本历史可追溯。
- `documentation-information-architecture`: 定义面向产品使用、工程学习、源码阅读和面试准备的文档结构与导航方式。

### Modified Capabilities
- None.

## Impact

- Affected code: `README.md`, `docs/**`, `openspec/changes/**` 中与发布/里程碑相关的内容。
- Affected systems: Git tag 历史、仓库文档导航、版本说明材料。
- Operational impact: 需要重写或重建部分历史 tag；需要迁移现有文档到新的目录结构。
