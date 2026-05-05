# 文档信息架构

本文定义 `agentOs` 仓库当前稳定使用的文档组织方式。

## 总原则

- `README.md` 只做首页和导航
- 详细内容全部下沉到 `docs/`
- 文档按“用途”分区，而不是按时间堆叠
- 同一主题只保留一个主维护入口

## 目录职责

## `docs/product/`

面向产品使用者。

包含：

- 产品是什么
- 怎么安装
- 怎么配置
- 怎么体验
- 怎么验收

## `docs/roadmap/`

面向维护者与版本管理。

包含：

- 版本历史
- tag 与 milestone 映射
- 发布规范
- 文档整理前后的核对记录
- 需要保留的里程碑说明

## `docs/learn/`

面向“想知道这个项目是怎么一步一步做出来”的读者。

包含：

- 分阶段构建历程
- change 地图

## `docs/architecture/`

面向“想看源码和执行链路”的读者。

包含：

- 系统分层
- 运行链路
- context engine
- tool runtime
- session 与记忆

## `docs/interview/`

面向面试、答辩和项目讲解。

包含：

- 核心功能与技术取舍
- LangChain / LangGraph 用法
- 与目标产品形态的差距
