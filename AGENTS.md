# linxira-package-center · Agent 开发规范

> **档位**:A · 系统源仓
> **本仓职责**:精选应用安装工具 Quick System Software Setup 的**选择 UI 与事务呈现**;
> Shelly 仍是通用软件中心。
> 通用约束见工作区总纲 `f:\Linxira-OS\AGENTS.md` 与发布规范 `linxira-os/docs/RELEASE_STANDARD.md`;
> 本文只写本仓特有内容。

## 职责与边界

- Phase 1 为**仅安装**的 PySide6 应用:默认 Catalog v3,以可展开三态分类树呈现已复核应用,
  生成并展示绑定 catalog 的计划、确认计划,再把提权事务**委托给 `linxira-components`**;
  **从不构造包命令,也从不调用 pacman**。
- 归属划分(`docs/BOUNDARIES.md` 有记录):
  - 本仓:`linxira-package-center` 拥有选择 UI、事务呈现、进度、历史、已安装态呈现与未来 Gaming Setup 工作流。
  - `linxira-catalog` 拥有可选元数据与策略;`linxira-components` 拥有计划、确认、提权 apply、校验与回执;
    `linxira-config-hub` 拥有配置/诊断 CLI,不做应用安装。
- **包卸载被有意禁用**,直至共享后端具备归属账本、依赖归因与漂移检测;已安装项显示为锁定的已选叶子,永不作为卸载提交。
- Catalog v3 事务使用 `org.linxira.component-selection.v1` 文档 + `linxira-components plan --selection`,
  **绝不用 `--application`**;选择绑定到精确的 catalog SHA-256 与 release。
- 已安装态可选,从 `LINXIRA_INSTALLED_STATE_PATH` 读取;未提供状态文档时 catalog 仍完全可用,Installed 视图为空。
- 可选复核信道视图为显式、只读的 opt-in;AUR / WPS / 专有/混合许可等第三方候选标注来源与许可后**保持禁用**。

## 目录布局

- `src/linxira-package-center`:单一入口脚本(无 `pyproject.toml`)
- `tests/`:`test_package_center.py`、`test_about_metadata.py`
- `data/`:`org.linxira.PackageCenter.desktop`、`org.linxira.PackageCenter.metainfo.xml`
- `docs/BOUNDARIES.md`、`requirements.txt`

## 本地校验

CI(分支 `main`,需 `libegl1` + `requirements.txt`)执行:

```sh
python -m pip install -r requirements.txt          # PySide6>=6.7,<7
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
python -m py_compile src/linxira-package-center
python -m compileall -q tests
```

本地带数据联调:

```sh
LINXIRA_CATALOG_PATH=/path/to/catalog.json \
LINXIRA_COMPONENTS_CLI=/path/to/linxira-components \
LINXIRA_INSTALLED_STATE_PATH=/path/to/installed-state.json \
python src/linxira-package-center
```

## 版本与发布

- 版本唯一来源是本仓根 `VERSION`(当前 `0.2.1`);`README.md` 里也标同一值。
- 改 `VERSION` 触发 `.github/workflows/release.yml`(分支 `main`)自动建 Release,进入 `[linxira]` 全自动链。**禁止手工 bump**。

## 禁区

- 不构造包命令、不直接调用 pacman,不提权(只经 `linxira-components` + polkit)。
- 不提供卸载/移除路径;不把第三方复核信道候选表示为"受支持的安装"。
- Catalog v3 分类根作为事务根,仅在 catalog 提供同 ID、同直接子项的 bundle 且全部子项 `optional` 时成立;
  契约缺失时**fail-closed**在调用后端之前,不得伪造 bundle 路径。
- 不引入 `cachyos` / `aur` / `seafoam`;不 `git add -A`。