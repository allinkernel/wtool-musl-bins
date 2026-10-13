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

## 动手前必须知道的三件事

1. **项目身份 = 路径**（ADR-0037）。改子目录名字 = 换身份，要用
   `wtool move tools/musl-bins/<旧> tools/musl-bins/<新>`，别直接 `mv`
   ——不然 `$WTOOL_HOME/wtool/…` 的 L1 链、`$WTOOL_STATE/…` 的账、rc 里那个块
   三处全悬空。

2. **`env.zsh` 和 `env.bash` 必须同改**。两份内容**逐字等价**（只差 shell 名与
   报错里那句提示），改动只落一份的后果是"那个 shell 的用户行为不一样"。

3. **sha256 必须现算**。`docs/tools.tsv` 和每个 `<工具>/wtool.xml` 里的 sha256
   是**下载之后 `sha256sum` 出来的**，不是抄来的。上游重发资产（同一个 tag
   换文件）这种事发生过 —— 升级时**重下重算**。

## 升级一个工具（bump）

三步，缺一不可：

```sh
# ① 看新 tag 有没有 x86_64 的 musl/静态资产（没有就**别升**，或者跳过这个工具）
gh api repos/<owner>/<repo>/releases --jq '.[0].tag_name, (.[0].assets[].name)'

# ② 下下来算 sha256（只落 /tmp）
curl -fsSL -H 'Accept: application/octet-stream' \
  "https://api.github.com/repos/<owner>/<repo>/releases/assets/<id>" -o /tmp/a
sha256sum /tmp/a

# ③ 三个地方一起改：
#    <工具>/wtool.xml 的 <muslbin url= tag= sha256=>（还有 member=，如果归档里换了名字）
#    <工具>/readme.md   的「当前版本」一节
#    docs/tools.tsv     那一行
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
