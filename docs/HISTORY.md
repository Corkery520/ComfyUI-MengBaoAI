# 萌宝AI 工具库与历史记录

统一悬浮工具框包含三个入口：

- 萌宝AI·提示词库
- 萌宝AI·素材库
- 萌宝AI·历史记录

桌面使用纵向工具框，窄屏使用横向工具框。悬停可以查看入口名称，名称随 ComfyUI 的 `Comfy.Locale` 设置切换中英文。打开库面板后可以直接切换入口；返回已打开的提示词面板不会重建表单，也不会改写未保存的内容。

## 历史记录

图像生成节点每次实际执行时创建一条记录，保存模型、实际请求提示词、生成参数、时间、进度和返回图片。一个批次的多张图片保存在同一记录中。原图尺寸和 Alpha 通道保留，缩略图只用于浏览，不替代原图。

支持搜索提示词、模型或 ID，按状态筛选、按时间排序、分页、多图预览和下载原始 PNG。面板打开时每 5 秒自动刷新，也可以关闭自动刷新或手动刷新；预览图片期间暂停定时刷新。关闭面板会清理刷新定时器。

状态包括生成中、已完成、部分完成和失败。生成失败说明图不作为图片归档。ComfyUI 重启时，未完成的历史任务标记为中断，不会重新提交任务或再次扣费。缓存命中而没有实际执行图像生成节点时，不会产生重复记录。

历史存放在 `ComfyUI/user/mengbaoai/history/`：

```text
history.sqlite3
images/<记录ID>-<图片序号>.png
thumbnails/<记录ID>-<图片序号>.png
```

不保存 API Key、鉴权头或完整 API 响应。历史图片与提示词属于用户数据，不进入 Git 仓库；备份时应保留整个历史目录。历史不自动删除，会随使用占用磁盘空间。

本功能从更新后实际执行的生成任务开始记录。旧版本未归档的图片无法仅从 ComfyUI 的节点缓存完整恢复，不会伪造旧历史。

## 安装与验证

新增后端路由后需要重启 ComfyUI，再按 `Ctrl+F5` 加载新的前端脚本。原有节点内部 ID、输入输出类型和工作流格式不变。

```powershell
python -m unittest discover -s tests -p 'test_history*.py'
node --test tests/test_frontend_history.mjs
```

HTTP 接口只用于读取本地历史：

- `GET /mengbao_history/items`：搜索、状态、排序及分页。
- `GET /mengbao_history/item/{record_id}`：记录详情。
- `GET /mengbao_history/file/{record_id}/{index}`：原图；`thumbnail=1` 返回缩略图，`download=1` 下载原图。

`tests/seed_history_preview.py` 仅在指定临时用户目录创建 UI 测试数据，通过模拟 API 返回验证图像生成归档，不调用付费 API。
