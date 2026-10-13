#!/usr/bin/env python3
"""从 `docs/tools.tsv` 生成每个工具子目录的 `readme.md`（**来源说明**）。

用法：
    python3 scripts/gen-readmes.py [--check] [工具名...]

为什么脚本生成而不是手写 30 份：结构完全一样（来源表 + 怎么装 + 怎么升级 + 为什么
用 musl），只有数据不同；手写 30 份的下场是升级时改了 3 份、剩下 27 份在撒谎。
**唯一权威是 `docs/tools.tsv`**，这份 readme 是它的人读展开版。

判据（用户 2026-10-13 明确要求）：**readme.md 里必须写清这个 muslbin
来自哪个项目、哪个 release 页**、哪个 tag、资产名、sha256、架构、license、怎么升级。
"""
import argparse
import os
import sys


def load_gen():
    """把 gen-files.py（文件名带连字符）当模块加载 —— 复用它的 COLS/read_catalog。"""
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "gen_files", os.path.join(here, "gen-files.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


README = """# `{tool}` —— {repo} 的 x86_64 静态二进制

> 这份文件是**给人读的来源说明**。机器读的是同目录的 `wtool.xml`（下载声明）
> 和仓库根目录的 `docs/tools.tsv`（**唯一权威表**，wtool.xml 由它生成）。
> ⚠️ 两处的 **tag 与 sha256 必须一致** —— 改一处没改另一处 = 装的和你以为的不是一个东西。

## 这个二进制从哪来

| 项 | 值 |
|---|---|
| 上游项目 | [`{repo}`](https://github.com/{repo}) |
| **release 页** | <https://github.com/{repo}/releases/tag/{tag}> |
| 本仓库钉的 tag | `{tag}` |
| 资产文件名 | `{asset}` |
| 资产直链 | <{url}> |
| 资产大小 | {bytes_h}（{bytes} 字节） |
| sha256 | `{sha256}` |
| 架构 | `x86_64` |
| 归档形状 | {archive} |
| 归档里取的成员 | {member_h} |
| 落点（`__output/` 下） | `{dest}` |
| 命令名 | `{cmd}` |
| 装完的版本串 | `{version}`（实测 `{version_cmd}` 的第一行） |
| license | **上游的：{license}** —— 本仓库只做声明，**不分发二进制** |{generate_row}

{note_block}\
## 怎么装

```sh
wtool download-release tools/musl-bins/{tool}   # 读 wtool.xml 的 <muslbin url>，按 sha256 校验 → __release/
wtool unpack-release   tools/musl-bins/{tool}   # 按 member/dest 解到 __output/{dest}
wtool install          tools/musl-bins/{tool}   # 建 L2 链：$WTOOL_HOME/usr/bin/{cmd}
```
{generate_howto}
装完 `{cmd}` 就能直接敲 —— `$WTOOL_HOME/usr/bin` 在 `PATH` 最前（ADR-0045 §1.2），
本项目**不自己往 PATH 里塞**。

> ⚠️ 头两条是**开发机命令**（D50）：有源码、能联网的机器用它们直接取上游。
> **断网机**不跑这两条 —— 它拿的是离线族的 `release-offline.zip`
> （解开 → `cp -a` 并进 `$WTOOL_HOME/wtool/` → `wtool install`）。

## 怎么升级（bump 三步）

1. **看上游新 tag 有没有 x86_64 的 musl/静态资产**：

   ```sh
   gh api repos/{repo}/releases --jq '.[0].tag_name, (.[0].assets[].name)'
   ```

   要的是 `x86_64-unknown-linux-musl`（Rust）或 `…_linux_x86_64` / `…_linux_amd64`
   （Go，`CGO_ENABLED=0` 编出来是静态的）。**没有就跳过这个版本**，
   **不要**拿 `-gnu` / `-glibc` 的顶上 —— 它依赖宿主 glibc，就失去这个项目存在的意义。
   {bump_warn}
2. **下下来、现算 sha256**（**不许照抄任何地方的旧值**，包括本文件的；只落 `/tmp`）：

   ```sh
   id=$(gh api repos/{repo}/releases/tags/<新tag> \\
        --jq '.assets[] | select(.name=="<新资产名>") | .id')
   curl -fsSL -H 'Accept: application/octet-stream' \\
     "https://api.github.com/repos/{repo}/releases/assets/$id" -o /tmp/{tool}.dl
   sha256sum /tmp/{tool}.dl && stat -c %s /tmp/{tool}.dl
   tar tzf /tmp/{tool}.dl | head        # 或 unzip -l —— 确认 member 还对不对
   ```

   （走 API 的资产端点是**故意的**：`github.com` 的直链有时不通，这个端点稳定。）

3. **改两处**：`docs/tools.tsv` 那一行（tag / asset / sha256 / bytes / member），
   然后 `python3 scripts/gen-files.py {tool}` 重新生成 `wtool.xml`。
   本文件里那几条**只在本文件里有**的信息（版本串、注意事项）也要跟着更新。
   最后在**临时** `$WTOOL_HOME` 里把上面三条命令跑一遍，确认 `{cmd} --version`
   打得出来 —— **别在真 `$HOME` 上试**。

## 为什么它进 `muslbin` 这个类型

上游发布的是**静态**二进制（Rust 的 `*-unknown-linux-musl`，或 Go 的
`CGO_ENABLED=0`）：不依赖宿主 glibc，同一份文件在 WSL、公司 Ubuntu 服务器上都能跑。
这正是 wtool 的使用场景（`harness/docs/adr/0045-wtool-redesign/pre_architecture.md` §4）。

判据不是"资产名里有没有 musl"，而是**`ldd` 认不认它**（认不出 = 静态）。
本仓库每个工具都实测过一遍（`{archive}`）。
"""

NOTE_TEMPLATE = "> ⚠️ **注意**：{note}\n\n"

# 每个工具**只在本文件里**有的那几条（版本串 / 注意事项）—— 表里放不下。
EXTRA = {
    "sd": "这个二进制 `--version` 打的是 **1.0.0**，而它来自上游 tag `v1.1.0`"
          "（上游 tag 与二进制里编进去的版本号不一致，2026-10-13 实测）。"
          "**以 tag + sha256 为准** —— sha256 对得上就是那份资产，别被版本串误导。",
    "age": "上游资产名里**没有 musl**（只有 `-linux-amd64`），但实测这个文件"
           "`readelf -d` 报 **There is no dynamic section**、`ldd` 不认它 —— "
           "即**纯静态的 Go 二进制**，不依赖宿主 glibc，符合 `muslbin` 的实质要求。"
           "资产包里还有 `age-keygen` / `age-plugin-*` 等，**本目录只导出 `age` 本体**"
           "（要 keygen 就再开一个子目录，别在一个项目里塞两个命令）。",
    "trippy": "命令叫 **`trip`**（不是 `trippy`），所以 `dest` 是 `usr/bin/trip`。"
              "另外：要**非 root** 用它那些要特权的功能（raw socket / 改 TTL），"
              "得给二进制加能力位："
              "`sudo setcap cap_net_raw,cap_net_admin+eip \"$WTOOL_HOME/usr/bin/trip\"`；"
              "不加也能跑（退化成 unprivileged 模式）。",
    "bottom": "命令叫 **`btm`**（不是 `bottom`），所以 `dest` 是 `usr/bin/btm`。"
              "想敲 `bottom` 就自己加个别名 —— 本项目不改 `PATH`、也不建别名。",
    "difftastic": "命令叫 **`difft`**（不是 `difftastic`），归档里也只有它一个成员。"
                  "把它接给 git 用：`git config --global diff.external difft`"
                  "（那是**用户自己**的 git 配置，wtool 不替你写 —— 新模型里 `$HOME` "
                  "不再有 wtool 建的软链）。",
    "fclones": "归档里留着整条 cargo 构建路径"
               "（`target/x86_64-unknown-linux-musl/release/fclones`），"
               "所以 `member` 要把前缀写全 —— 声明式解包会剥掉 `member` 里最后一个 `/` "
               "之前的部分，落到 `dest` 的因此是裸的那个文件名。",
    "fzf": "这个目录带两条 `<generate>`（fzf 的补全 / 按键绑定脚本，D33）："
           "`fzf --zsh` / `fzf --bash` 在 **`wtool install` 的时候**生成到 `__output/` 下，"
           "再由本项目自己的 `env.{zsh,bash}` 去 source（各 source 自己那一份）。"
           "生成物**进账本**、`wtool uninstall` 删掉 —— 所以补全是「装的时候」才有的，"
           "不是 source 的时候现算的。另：`terminal/fzf`（老项目）**还在提供 `fzf` 命令**，"
           "把 `fzf` 迁到本目录是一次性切换时的事（D34）。",
    "navi": "归档里那个成员叫 **`./navi`**（`member` 就写 `./navi` —— 引擎两边都会归一："
            "去 `./` 前缀）。`<generate>` 跑 `navi widget <shell>`：它注册 "
            "`_navi_widget` 并把 **Ctrl-G** 绑上去（在 zsh 的 `bindkey` / bash 的 "
            "`bind -x` 里）。作弊条本身要用户自己攒（`navi repo add` / `~/.local/share/navi`），"
            "wtool 不替他拉任何仓库。",
    "starship": "⚠️ **它会改提示符**：`<generate>` 跑的 `starship init <shell>` 会把 "
                "`PROMPT` / `PS1` 接管（这就是它的用途）。装它的机器上提示符**一定**变样，"
                "不想要就别装 —— 别的 muslbin 都不会动 shell 的显示。"
                "它是本仓库唯一 **ISC** 许可的（其余都是 MIT / Apache-2.0 / BSD）。"
                "配置在 `~/.config/starship.toml`（**用户自己**的，wtool 不写）。",
    "atuin": "归档里那个成员带一层目录前缀（`atuin-x86_64-unknown-linux-musl/atuin`）。"
             "⚠️ 解出来是 **41 MB**（压缩后 16.7 MB）—— 本仓库里最大的一个。"
             "`<generate>` 跑 `atuin init <shell>`。它的历史默认存在**本地 SQLite**"
             "（`~/.local/share/atuin`），要用同步得自己 `atuin register` / `atuin login`"
             "（那是**用户自己**的事，wtool 不碰）。",
    # ---- 第 ⑦.3 块：hook 类（<generate> 出各自的 shell 集成）----
    "zoxide": "归档里**也有** `completions/zoxide.{bash,fish,nu,ps1,ts,elv}` 和 man 页，"
              "但本项目**不用它们** —— shell 集成是 `<generate>` 在**安装时**跑 "
              "`zoxide init <shell>` 现生成的（D33）：补全、`z` / `zi` 别名、`chpwd` "
              "钩子（`__zoxide_hook`）都在那份产物里。装完 `z` / `zi` 就可用，"
              "但 `zoxide` 得先在数据库里攒过目录（`zoxide add`）才有东西可跳。",
    "direnv": "上游发的是**裸文件**（`direnv.linux-amd64`，没有归档）→ `member` 留空，"
              "解出来直接落 `usr/bin/direnv`。它的 `--version` 只打版本号（`2.38.2`），"
              "不带命令名。`<generate>` 跑 `direnv hook <shell>`：注册的是 "
              "`_direnv_hook`，真正干活要用户在项目目录里放 `.envrc` 并 `direnv allow`"
              "（那是**用户自己**的事，wtool 不替他写）。",
}


TABLE_BEGIN = "<!-- BEGIN TOOLS-TABLE（由 scripts/gen-readmes.py --table 生成，别手改这一段） -->"
TABLE_END = "<!-- END TOOLS-TABLE -->"


def render_table(rows):
    """仓库根 README.md 里那张「工具总表」（人读版，数据还是 docs/tools.tsv）。

    表在 README.md 里由上面两个标记包着 —— `--check` 会比对，漂了会报。
    """
    out = ["| 工具 | 命令 | 上游项目（release 页） | tag | 资产 | 静态？ |",
           "|---|---|---|---|---|---|"]
    for r in rows:
        cmd = r["dest"].rsplit("/", 1)[-1]
        out.append("| `%s` | `%s` | [%s](https://github.com/%s/releases/tag/%s) | `%s` | `%s` | %s |"
                   % (r["tool"], cmd, r["repo"], r["repo"], r["tag"],
                      r["tag"], r["asset"], r["archive"]))
    return "\n".join(out) + "\n"


def main():
    g = load_gen()
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=os.path.join(g.os.path.dirname(
        g.os.path.abspath(g.__file__)), g.os.pardir, "docs", "tools.tsv"))
    ap.add_argument("--out", default=os.path.join(g.os.path.dirname(
        g.os.path.abspath(g.__file__)), g.os.pardir))
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--table", action="store_true",
                    help="把仓库 README.md 里那张工具总表打到 stdout（--check 时比对 README.md）")
    ap.add_argument("tools", nargs="*")
    args = ap.parse_args()

    rows = g.read_catalog(args.catalog)
    if args.tools:
        want = set(args.tools)
        rows = [r for r in rows if r["tool"] in want]

    readme = os.path.join(args.out, "README.md")
    if args.table:
        table = render_table(rows)
        if not args.check:
            sys.stdout.write(table)
            return 0
        # --check：README.md 里那段（两个标记之间）必须和渲染结果逐字一致
        if not os.path.isfile(readme):
            sys.stderr.write("没有 %s —— 工具总表没地方可比\n" % readme)
            return 1
        with open(readme, encoding="utf-8") as fh:
            text = fh.read()
        if TABLE_BEGIN not in text or TABLE_END not in text:
            sys.stderr.write("%s 里没有工具总表的两个标记（%s / %s）\n"
                             % (readme, TABLE_BEGIN, TABLE_END))
            return 1
        have = text.split(TABLE_BEGIN, 1)[1].split(TABLE_END, 1)[0].lstrip("\n")
        if have != table:
            sys.stderr.write("DRIFT %s 里的工具总表和 docs/tools.tsv 对不上"
                             "（跑 `python3 scripts/gen-readmes.py --table` 重新贴）\n" % readme)
            return 1
        print("OK   %s 里的工具总表 = docs/tools.tsv 的渲染" % readme)
        return 0

    extra = os.path.join(g.os.path.dirname(g.os.path.abspath(g.__file__)), "versions.tsv")
    vers = {}
    if os.path.isfile(extra):
        with open(extra, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip() or line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 2:
                    vers[parts[0]] = parts[1]

    rc = 0
    for row in rows:
        tool = row["tool"]
        if row["sha256"] == "PENDING" or len(row["sha256"]) != 64:
            sys.stderr.write("跳过 %s：sha256 还没算出来\n" % tool)
            rc = 1
            continue
        cmd = row["dest"].rsplit("/", 1)[-1]
        member_h = ("`%s`" % row["member"]) if row["member"] else "—（裸二进制，没有归档）"
        note = EXTRA.get(tool, "")
        note_block = NOTE_TEMPLATE.format(note=note) if note else ""
        # 带 shell 集成的工具（表里 generate 列非空）：表里多一行 + 装法下面多一段。
        # ⚠️ 两个都**自带前导换行**（不是整行占位）：空格工具那边一个字节都不多出来，
        #    否则 30 份没 hook 的 readme 会平白多一个空行。
        gens = g.parse_generate(row.get("generate", ""))
        generate_row = generate_howto = ""
        if gens:
            generate_row = ("\n| shell 集成（`<generate>`，D33） | %s —— **安装时**生成到 "
                            "`__output/%s.{zsh,bash}`，由本项目自己的 `env.{zsh,bash}` 去 source |"
                            % (" / ".join("`%s`" % c for _s, c in gens), tool))
            generate_howto = (
                "\n> ⚠️ **这个项目带 `<generate>`**：`wtool install` 的时候会跑 %s，\n"
                "> 把输出写到 `__output/%s.zsh` / `__output/%s.bash`（进账本，`wtool uninstall` 删掉）。\n"
                "> `env.zsh` / `env.bash` 各自 source 自己那一份 —— 所以 shell 集成是\n"
                "> **装的时候**才有的，**不是** source 的时候现算的。\n"
                % (" / ".join("`%s`" % c for _s, c in gens), tool, tool))
        bump_warn = ""
        if not row["member"]:
            bump_warn = ("\n   > 这个资产是**裸二进制**（不是归档）—— 换 tag 时"
                         "**必须挑同一个形状的资产**（有些上游同时发裸文件和 `.tar.gz`）。\n")
        text = README.format(
            tool=tool, repo=row["repo"], tag=row["tag"], asset=row["asset"],
            url="https://github.com/%s/releases/download/%s/%s"
                % (row["repo"], row["tag"], row["asset"]),
            bytes=row["bytes"], bytes_h="%.1f MiB" % (int(row["bytes"]) / 1048576.0),
            sha256=row["sha256"], archive=row["archive"], member_h=member_h,
            dest=row["dest"], cmd=cmd, license=row["license"] or "见上游仓库",
            version=vers.get(tool, "（见上游）"), version_cmd="%s --version" % cmd,
            note_block=note_block, bump_warn=bump_warn,
            generate_row=generate_row, generate_howto=generate_howto)
        p = os.path.join(args.out, tool, "readme.md")
        if args.check:
            if os.path.isfile(p):
                with open(p, encoding="utf-8") as fh:
                    old = fh.read()
            else:
                old = None
            if old != text:
                print("DRIFT %s" % p)
                rc = 1
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
    return rc


if __name__ == "__main__":
    sys.exit(main())
