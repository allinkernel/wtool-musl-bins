# AGENTS.md —— 给 AI 助手看的那一份

> 这个仓库是 wtool 工作区里的一个**项目**（`tools/musl-bins`）。
> 工作区级规矩看 `~/self/wtool/AGENTS.md` 和 `~/.dsh/AGENTS.md`，这里只写**这个仓库特有**的事。

## 30 秒认识它

- **一个工具 = 一个 wtool 项目**：`<工具>/wtool.xml` 各自一份，引擎按磁盘上的
  `wtool.xml` 扫项目（所以 `wtool install tools/musl-bins/bat` 是合法的项目 id）。
- **`kind="muslbin"`**（ADR-0045 §1.4）：产物**不是**本仓库编的，是从上游 release
  下下来的静态二进制 → `__output/usr/bin/<工具>` → `<export_bin>` 建一条 L2 链。
- **只提交文本**。`__output/`、`__release/`、`*.tar.gz`、`*.zip` 都不进 git
  （见 `.gitignore`）。

## 动手前必须知道的四件事

1. **项目身份 = 路径**（ADR-0037）。改子目录名字 = 换身份，要用
   `wtool move tools/musl-bins/<旧> tools/musl-bins/<新>`，别直接 `mv`
   ——不然 `$WTOOL_HOME/wtool/…` 的 L1 链、`$WTOOL_STATE/…` 的账、rc 里那个块
   三处全悬空。

2. **`env.zsh` 和 `env.bash` 必须同改**。两份内容**逐字等价**（只差 shell 名与
   报错里那句提示），改动只落一份的后果是"那个 shell 的用户行为不一样"。

3. **sha256 必须现算**。`docs/tools.tsv` 和每个 `<工具>/wtool.xml` 里的 sha256
   是**下载之后 `sha256sum` 出来的**，不是抄来的。上游重发资产（同一个 tag
   换文件）这种事发生过 —— 升级时**重下重算**。

4. **`<工具>/` 下的三份文件都是生成物**（第 ⑦.3 块起，包括 `readme.md`）：
   `docs/tools.tsv` 是**唯一权威**，改完跑
   `python3 scripts/gen-files.py <工具> && python3 scripts/gen-readmes.py <工具>`。
   手改生成物 = 下次生成时被打回去（`--check` 会报 DRIFT）。

## 带 shell 集成的工具（hook 类）

`zoxide` / `direnv` / `atuin` / `starship` / `navi` / `fzf` 这种要在 shell 里注册
函数/别名的，**不用手写任何东西** —— 在 `docs/tools.tsv` 的 `generate` 列写：

```
zsh:zoxide init zsh;bash:zoxide init bash
```

`gen-files.py` 会自动生成 `<generate dest="__output/<工具>.<shell>" cmd="…"/>`
和 `env.<shell>` 末尾那段 source 块（D33 / D41）：命令在 **`wtool install` 时**跑，
产物落 `__output/`、进账本、`uninstall` 删掉。

- **zsh 和 bash 两份都要写**（只写一份 = 另一个 shell 的用户没有集成）
- 命令里写**命令名**，不写绝对路径 —— 跑的时候 `PATH` 前面就是
  `$WTOOL_HOME/usr/bin`（用的是刚链上的那份二进制）
- 加完在容器里真验一次（`zsh -f -i` / `bash --noprofile --norc -i` 里 source 完
  看函数有没有注册）：**非交互 shell 里一个定义都不会有**，那不是坏了

## 升级一个工具（bump）

三步，缺一不可：

```sh
# ① 看新 tag 有没有 x86_64 的 musl/静态资产（没有就**别升**，或者跳过这个工具）
gh api repos/<owner>/<repo>/releases --jq '.[0].tag_name, (.[0].assets[].name)'

# ② 下下来算 sha256（只落 /tmp）
curl -fsSL -H 'Accept: application/octet-stream' \
  "https://api.github.com/repos/<owner>/<repo>/releases/assets/<id>" -o /tmp/a
sha256sum /tmp/a

# ③ 改**一处**：docs/tools.tsv 那一行（tag / asset / sha256 / bytes / member）
#    然后重新生成（**别手改 <工具>/ 下的文件**，它们是生成物）：
python3 scripts/gen-files.py   <工具>
python3 scripts/gen-readmes.py <工具>
# ④ 实测的 `<命令> --version` 第一行补进 scripts/versions.tsv，再跑一次 ③
```

改完在**临时** `$WTOOL_HOME` 里跑一遍 `download-release` → `unpack-release` →
`install`，确认 `$WTOOL_HOME/usr/bin/<工具> --version` 打得出来。

## 别做

| 别做 | 为什么 |
|---|---|
| 往仓库里放二进制 | 这个仓库存在的意义就是"只放声明，二进制从上游取"；几百 MB 进 git 洗不掉 |
| 用第三方重打包的资产 | 来源不可信，URL 与 sha256 都不稳定 |
| 用 `-gnu` / `-glibc` 资产顶替 | 它依赖宿主 glibc，就失去 `muslbin` 这个类型的意义 |
| 往 `PATH` 里塞 `$WTOOL_HOME/usr/bin` | 引擎统一放最前（ADR-0045 §1.2），项目再塞一遍会重复 |
| 在真 `$HOME` 上试装 | 用临时 `WTOOL_HOME` + `WTOOL_STATE`，或 `docker run --rm` |
| `git push` | 改动只提交到 `ds_dev`，合不合由用户定（工作区级规矩） |
