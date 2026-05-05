# 发布检查清单

本清单用于未来继续打 tag 或整理版本时自检。

## 发布前检查

- `make test` 通过
- `bash scripts/verify_env.sh` 通过
- `agentos --help` 和 `agentos status` 正常
- `README.md` 与当前产品形态一致
- `docs/roadmap/tag-and-milestone-map.md` 已更新
- `openspec/changes/.../tasks.md` 与实现状态一致
- `.agentos/` 等本地状态文件未被误提交

## 打 tag 标准

只有满足以下条件才适合创建新 tag：

- 当前阶段有明确的新能力，而不是零散小修
- 至少有一条稳定体验路径
- 文档已经写清楚“完成了什么、怎么体验、怎么验证”
- 不会让后续读者对历史阶段产生歧义

## 打 tag 流程

1. 完成功能或文档收尾
2. 执行测试与文档核对
3. 提交聚焦 commit
4. 创建 tag
5. 推送 `main`
6. 推送 tag

## 历史修正注意事项

如果需要重写历史 tag：

- 先更新映射表
- 再执行本地 tag 删除与重建
- 再做两轮核对
- 最后同步远端
