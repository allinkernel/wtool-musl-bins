#!/usr/bin/env python3
"""从**唯一权威表** `docs/tools.tsv` 生成每个工具子目录的 `wtool.xml` + `env.{zsh,bash}`。

用法：
    python3 scripts/gen-files.py [--check] [工具名...]

为什么要有这个脚本（而不是手写 30 份文件）：这 30 份 `env.zsh` / `env.bash` 结构完全相同，
只有工具名不同，而"两份逐字等价"是硬要求。手写 = 60 份可以互相漂移的副本。
所以：**模板在本脚本 + `scripts/env-skeleton.txt`（一处），数据在 `docs/tools.tsv`（一处）**。

带 shell 集成的工具（`fzf` / `zoxide` / `direnv` / `atuin` / `starship` / `navi` 这种）
也走这里：表里的 `generate` 列 → `<generate>` 声明 + `env.*` 末尾那段 source 块。
（第 ⑦.2 块 fzf 那两份 env 是手写的，于是和本脚本漂移了 —— 第 ⑦.3 块收回脚本生成。）

⚠️ `readme.md` 由 `scripts/gen-readmes.py` 生成（不是本脚本，也不是手写 30 份）。

⚠️ 本脚本**不参与安装**：它只是仓库维护工具。装的时候引擎不需要它。
"""
import argparse
import os
import sys

COLS = ("tool", "repo", "tag", "asset", "sha256", "bytes", "member", "dest",
        "archive", "license", "note", "generate")

# `<generate>`（ADR-0045 D33 / D41）：**安装时**跑的命令，输出落 `__output/`，
# 由本项目自己的 `env.<shell>` 去 source。表里的 `generate` 列就是它：
#
#     zsh:zoxide init zsh;bash:zoxide init bash
#
# —— `<shell>:<命令>` 若干条，`;` 隔开；空白 = 这个工具不需要 shell 集成。
# 加一条 `zsh:`/`bash:` 就自动多一条 `<generate>` + env 里的 source 块，
# 手不用碰任何 `<工具>/` 下的文件（它们是生成物）。
GENERATE_SHELLS = ("zsh", "bash")
# 生成物一律叫 `<工具>.<shell>`；env 里那个中转变量叫 `WTOOL_<工具大写>_RC`
# （工具名里的 `-` 换成 `_`，否则不是合法的 shell 变量名）。
HOOK_BLOCK = """
# ---------------------------------------------------------------------------
# shell 集成：**安装时生成**，这里只负责 source（D33 / D41）
#
# 生成物落在 __output/ 下（不是源码树）：它是**安装期产物**，不进 git。
# 生成它的命令写在 wtool.xml 里：
#     <generate dest="__output/{tool}.{shell}" cmd="{cmd}"/>
# `wtool install` 时跑（产物进账本）、`wtool uninstall` 时删。
#
# ‼️ 生成物读不到就**说一句再跳过**，绝不静默：静默的症状是"{tool} 装好了，
#    但 shell 集成没生效"，而这里一声不吭 —— 和本文件顶部那段是同一个理由
#    （半装状态最难查）。真装过的话它一定在。
# ---------------------------------------------------------------------------
# 单独 source（不经 wtool 块）时的兜底：L1 路径就是项目在 $WTOOL_HOME 里的稳定地址
[ -n "${{WTOOL_PROJECT_DIR:-}}" ] || WTOOL_PROJECT_DIR="$WTOOL_HOME/wtool/tools/musl-bins/{tool}"
WTOOL_{upper}_RC="$WTOOL_PROJECT_DIR/__output/{tool}.{shell}"
if [ -r "$WTOOL_{upper}_RC" ]; then
    source "$WTOOL_{upper}_RC"
else
    echo "wtool: {tool} 的 shell 集成还没生成：$WTOOL_{upper}_RC" >&2
    echo "       它是 wtool install 时按 wtool.xml 的 <generate> 生成的；" >&2
    echo "       跑一次 wtool install tools/musl-bins/{tool} 就有了（不用重下二进制）。" >&2
fi
unset WTOOL_{upper}_RC
"""
GENERATE_LINE = '  <generate dest="__output/{tool}.{shell}"{pad} cmd="{cmd}"/>\n'
# 这段注释跟着 `<generate>` 那几行走（说清"什么时候跑、在什么环境里跑、失败了会怎样"）。
GENERATE_BLOCK = """
  <!-- shell 集成由**本项目自己的 env.{zsh,bash}** 去 source（D33）：
       生成物落在 __output/ 下（D41），不进 git、卸载时删掉。
       cmd 在**安装时**跑，cwd = 项目根，PATH 前面是 $WTOOL_HOME/usr/bin
       （所以跑的就是刚链上的那一份二进制）。
       失败 / 产物是空的 → install 当场非 0（不会留半个生成物）。
       ⚠️ XML 注释里不能出现两个连续的减号，所以这里不写命令原文。 -->
"""
GENERATE_COMMENT = """
  ⚠️ 另有 {n} 条 <generate>（{tool} 的 shell 集成，D33 / D41）：生成物落在
     __output/ 下、**装的时候**才生成（进账本，卸载时删掉），
     再由本项目自己的 env.{{zsh,bash}} 去 source。"""

WTOOL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!--
  {tool} —— 上游 release 的 x86_64 静态二进制（② 类 `kind="muslbin"`，ADR-0045 §1.4）。

  来源：{repo}   tag {tag}   license {license}
  当前版本、release 页、资产名与 sha256 见同目录的 readme.md（**先读它再升级**）。

  三件事别改坏：
    · `<muslbin>` 是**下载声明**（`download-release` 读它，并按 sha256 校验）。
      `tag` 必须钉死；`url` 必须指到**那个 tag** 的资产（不许用 latest）。
      `member` = 归档里要取的那个成员，`dest` = 解到 `__output/` 下的哪个相对路径。
    · `<export_bin src="__output/{dest}">` 的 src **必须在 __output/ 下**（D40）——
      它是"下载解出来的产物"，不是源码。落点由标签决定：$WTOOL_HOME/usr/bin/{tool}。
    · **本文件不写 PATH**：$WTOOL_HOME/usr/bin 由引擎统一放最前（ADR-0045 §1.2）。
{generate_comment}-->
<wtool schema="1" kind="muslbin" priority="60">

  <zshrc  src="env.zsh"/>
  <bashrc src="env.bash"/>

  <muslbin url="{url}"
           tag="{tag}" sha256="{sha256}"
           {member_attr}dest="{dest}" arch="x86_64"/>
{generate}
  <export_bin src="__output/{dest}"/>
</wtool>
"""

def parse_generate(spec):
    """表里的 `generate` 列 → `[(shell, cmd), …]`（顺序 = 列里的顺序）。

    格式：`<shell>:<命令>`，多条用 `;` 隔开。写错了**这里就报错**，
    而不是生成一份坏清单（坏清单要跑到安装时才炸）。
    """
    out = []
    for item in (spec or "").split(";"):
        item = item.strip()
        if not item:
            continue
        shell, sep, cmd = item.partition(":")
        shell, cmd = shell.strip(), cmd.strip()
        if not sep or shell not in GENERATE_SHELLS or not cmd:
            raise ValueError("generate 列写得不对：%r\n"
                             "  期望 `<shell>:<命令>`（shell ∈ %s），多条用 `;` 隔开"
                             % (item, " / ".join(GENERATE_SHELLS)))
        out.append((shell, cmd))
    dup = [s for s in GENERATE_SHELLS if [x[0] for x in out].count(s) > 1]
    if dup:
        raise ValueError("generate 列里同一个 shell 出现了两次：%s" % " ".join(dup))
    return out


def render_generate(tool, spec):
    """→ (`<generate>` 那几行（含注释）, {shell: env 文件末尾那段 source 块})。

    ⚠️ source 块要**按 shell 分开**：`env.zsh` 只 source `<工具>.zsh`、
    `env.bash` 只 source `<工具>.bash`。两边都塞 = bash 的初始化脚本被 zsh
    执行一遍（反过来也一样），那是错的行为，不是"更兼容"。
    """
    gens = parse_generate(spec)
    if not gens:
        return "", {}
    pad = max(len(s) for s, _c in gens)
    lines = [GENERATE_LINE.format(tool=tool, shell=s, cmd=c, pad=" " * (pad - len(s)))
             for s, c in gens]
    hooks = {s: HOOK_BLOCK.format(tool=tool, shell=s, cmd=c,
                                  upper=tool.upper().replace("-", "_"))
             for s, c in gens}
    return GENERATE_BLOCK + "".join(lines), hooks


def read_catalog(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            while len(parts) < len(COLS):
                parts.append("")
            row = dict(zip(COLS, parts))
            if row["tool"]:
                rows.append(row)
    return rows


def xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def render_xml(row):
    tool = row["tool"]
    member_attr = ('member="%s" ' % xml_escape(row["member"])) if row["member"] else ""
    generate, _hook = render_generate(tool, row["generate"])
    generate_comment = ""
    if generate:
        generate_comment = GENERATE_COMMENT.format(
            tool=tool, n=len(parse_generate(row["generate"])))
    return WTOOL_XML.format(
        tool=tool, repo=row["repo"], tag=row["tag"],
        license=row["license"] or "见上游仓库",
        url=xml_escape("https://github.com/%s/releases/download/%s/%s"
                       % (row["repo"], row["tag"], row["asset"])),
        sha256=row["sha256"], member_attr=member_attr, dest=row["dest"],
        generate=generate, generate_comment=generate_comment)


def render_env(tool, shell, other, rcfile, hook_block):
    skeleton = os.path.join(os.path.dirname(os.path.abspath(__file__)), "env-skeleton.txt")
    with open(skeleton, encoding="utf-8") as fh:
        text = fh.read()
    return (text.replace("<TOOL>", tool).replace("<SHELL>", shell)
                .replace("<OTHER>", other).replace("<RCFILE>", rcfile)
                .replace("<HOOK_BLOCK>", hook_block))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), os.pardir, "docs", "tools.tsv"))
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), os.pardir))
    ap.add_argument("--check", action="store_true",
                    help="只比对已存在的文件、不写（用来查漂移）")
    ap.add_argument("tools", nargs="*")
    args = ap.parse_args()

    rows = read_catalog(args.catalog)
    if args.tools:
        want = set(args.tools)
        missing = want - {r["tool"] for r in rows}
        if missing:
            sys.stderr.write("表里没有这些工具: %s\n" % " ".join(sorted(missing)))
            return 1
        rows = [r for r in rows if r["tool"] in want]

    rc = 0
    for row in rows:
        if row["sha256"] == "PENDING" or len(row["sha256"]) != 64:
            sys.stderr.write("跳过 %s：sha256 还没算出来（%r）\n"
                             % (row["tool"], row["sha256"]))
            rc = 1
            continue
        d = os.path.join(args.out, row["tool"])
        os.makedirs(d, exist_ok=True)
        _gen, hooks = render_generate(row["tool"], row["generate"])
        files = {
            "wtool.xml": render_xml(row),
            "env.zsh": render_env(row["tool"], "zsh", "bash", "zshrc",
                                  hooks.get("zsh", "")),
            "env.bash": render_env(row["tool"], "bash", "zsh", "bashrc",
                                   hooks.get("bash", "")),
        }
        for name, text in files.items():
            p = os.path.join(d, name)
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
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text)
    return rc


if __name__ == "__main__":
    sys.exit(main())
