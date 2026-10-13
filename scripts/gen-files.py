#!/usr/bin/env python3
"""从**唯一权威表** `docs/tools.tsv` 生成每个工具子目录的 `wtool.xml` + `env.{zsh,bash}`。

用法：
    python3 scripts/gen-files.py [--check] [工具名...]

为什么要有这个脚本（而不是手写 30 份文件）：这 30 份 `env.zsh` / `env.bash` 结构完全相同，
只有工具名不同，而"两份逐字等价"是硬要求。手写 = 60 份可以互相漂移的副本。
所以：**模板在本脚本 + `scripts/env-skeleton.txt`（一处），数据在 `docs/tools.tsv`（一处）**。

⚠️ `readme.md` **不由它生成** —— 那份是给人读的（来源、release 页、完整 URL、升级步骤），
   每个工具的内容不一样，手写；本脚本只保证 `wtool.xml` 和 `env.*` 不漂移。

⚠️ 本脚本**不参与安装**：它只是仓库维护工具。装的时候引擎不需要它。
"""
import argparse
import os
import sys

COLS = ("tool", "repo", "tag", "asset", "sha256", "bytes", "member", "dest",
        "archive", "license", "note")

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

GENERATE_FZF = """
  <!-- 补全 / 按键绑定脚本由**本项目自己的 env.{zsh,bash}** 去 source（D33）：
       生成物落在 __output/ 下（D41），不进 git、卸载时删掉。
       ⚠️ 执行逻辑在第 ⑦.2 块接线，在那之前这两条**只解析、不校验、不执行**。 -->
  <generate dest="__output/fzf.zsh"  cmd="fzf --zsh"/>
  <generate dest="__output/fzf.bash" cmd="fzf --bash"/>
"""


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
    generate = generate_comment = ""
    if tool == "fzf":
        generate = GENERATE_FZF
        generate_comment = ("\n  ⚠️ 另有两条 <generate>（fzf 的补全脚本，D33）—— 它是 ③ 类里\n"
                            "     `fzf` 存在的理由，所以本轮就按设计写进来。")
    return WTOOL_XML.format(
        tool=tool, repo=row["repo"], tag=row["tag"],
        license=row["license"] or "见上游仓库",
        url=xml_escape("https://github.com/%s/releases/download/%s/%s"
                       % (row["repo"], row["tag"], row["asset"])),
        sha256=row["sha256"], member_attr=member_attr, dest=row["dest"],
        generate=generate, generate_comment=generate_comment)


def render_env(tool, shell, other, rcfile):
    skeleton = os.path.join(os.path.dirname(os.path.abspath(__file__)), "env-skeleton.txt")
    with open(skeleton, encoding="utf-8") as fh:
        text = fh.read()
    return (text.replace("<TOOL>", tool).replace("<SHELL>", shell)
                .replace("<OTHER>", other).replace("<RCFILE>", rcfile))


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
        files = {
            "wtool.xml": render_xml(row),
            "env.zsh": render_env(row["tool"], "zsh", "bash", "zshrc"),
            "env.bash": render_env(row["tool"], "bash", "zsh", "bashrc"),
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
