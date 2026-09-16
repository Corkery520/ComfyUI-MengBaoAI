# Comfy Registry / Manager 发布指南

本仓库是唯一主节点包，Registry ID 为 `mengbaoai`，Publisher ID 为 `corkery520`。旧 `mengbao-image-api` 是独立 Legacy 包，不用于总包升级，也不向旧 Git 远端推送总包功能。

## 首次发布

1. 在 [Comfy Registry](https://registry.comfy.org/) 登录并确认 Publisher ID 是 `corkery520`。若尚未创建，需要先创建；不要使用其他 Publisher 的密钥。
2. 为该 Publisher 创建 Registry Publishing API Key。它只用于节点发布，**不是生图 API Key，也不是 GitHub Token**。
3. 在 [本仓库 Actions Secrets](https://github.com/Corkery520/ComfyUI-MengBaoAI/settings/secrets/actions) 新增 `REGISTRY_ACCESS_TOKEN`，填入发布密钥。不把值发到聊天、源码、工作流或日志中。
4. 确认 `main` 的 **Node pack checks** 全部通过。在 [Publish to Comfy Registry](https://github.com/Corkery520/ComfyUI-MengBaoAI/actions/workflows/publish_action.yml) 点击 **Run workflow**，选择 `main`。
5. 等待平台处理，检查版本状态与下载接口，再宣布 Manager 可搜索安装。上传成功不等于安全扫描已经完成；若状态为 Pending / Flagged，按平台返回的 `status_reason` 处理。

发布工作流缺少密钥时明确失败，并显示：

```text
REGISTRY_ACCESS_TOKEN is not configured. No Registry version has been published.
```

配置 Secret 后重新运行即可，不需要重新提交生图密钥或重复修改节点代码。发布工作流使用官方 `Comfy-Org/publish-node-action`，上传前执行完整测试。

## 验证真实上架

可在浏览器或 HTTP 客户端检查公开接口：

```text
GET https://api.comfy.org/nodes/mengbaoai
GET https://api.comfy.org/nodes/mengbaoai/install?version=1.0.0
```

检查仓库和 Publisher 归属正确，目标版本为 `NodeVersionStatusActive`，`downloadUrl` 非空且可下载。下载解压后应有根入口、`nodes/`、`api/`、`utils/`、`web/js/`、中英文 `locales/`、依赖清单与 LICENSE；安装后应注册 17 个节点。不要只看 GitHub Actions 的绿色结果判断是否已经上架。

Manager 搜索关键词：`MengBaoAI`、`mengbaoai`、`萌宝AI`。未显示时先确认 Registry 版本可安装，再刷新 Manager 的远程数据库及检查过滤条件。发布到 Registry 会供支持 Registry 的 Manager 使用；旧版 Manager 需要升级。画布里的节点搜索别名不能替代 Registry 上架。

## 后续版本

- 保持 Registry ID `mengbaoai` 和已经发布的内部节点 ID 不变。
- 发布版本使用 `X.Y.Z`，每个版本发布后不可覆盖。首版为 `1.0.0`，修复发布时递增版本并更新 CHANGELOG。
- 更新 `pyproject.toml` 并推送 `main` 会触发正式发布；其他代码提交仅触发 CI。也可以手动运行发布工作流。
- 同一版本已经发布时，不要重复运行试图覆盖；检查现有版本或递增版本后发布。
- 新增节点时更新安装包检查的稳定 ID 清单及两套 locale 定义。

## 安装包与用户数据

官方发布工具默认打包 Git 已跟踪文件；`.comfyignore` 排除测试、CI、缓存、环境文件和开发产物，保留完整运行文件及使用文档。`tests/check_registry_package.py` 使用 Git 忽略解析器构建过滤后的 ZIP，在临时用户目录验证实际加载、17 个内部 ID、分类、中英文控件与输出、搜索别名和敏感信息。

用户数据只保存在 `ComfyUI/user/mengbaoai/`，不进入安装包。升级不得覆盖 `.env`、提示词、素材、历史记录或复刻草稿。停用旧独立插件后再安装总包，避免重复 ID 和路由。具体安装及迁移见 [README](../README.md)。

## 官方参考

- [Registry 发布流程](https://docs.comfy.org/registry/publishing)
- [pyproject.toml 规范](https://docs.comfy.org/registry/specifications)
- [节点安装版本接口](https://docs.comfy.org/registry/api-reference/nodes/returns-a-node-version-to-be-installed)
- [ComfyUI-Manager](https://github.com/Comfy-Org/ComfyUI-Manager)
