# `fdfind` —— sharkdp/fd 的 x86_64 静态二进制

> 这份文件是**给人读的来源说明**。机器读的是同目录的 `wtool.xml`（下载声明）
> 和仓库根目录的 `docs/tools.tsv`（**唯一权威表**，wtool.xml 由它生成）。
> ⚠️ 两处的 **tag 与 sha256 必须一致** —— 改一处没改另一处 = 装的和你以为的不是一个东西。

## 这个二进制从哪来

| 项 | 值 |
|---|---|
| 上游项目 | [`sharkdp/fd`](https://github.com/sharkdp/fd) |
| **release 页** | <https://github.com/sharkdp/fd/releases/tag/v10.5.0> |
| 本仓库钉的 tag | `v10.5.0` |
| 资产文件名 | `fd-v10.5.0-x86_64-unknown-linux-musl.tar.gz` |
| 资产直链 | <https://github.com/sharkdp/fd/releases/download/v10.5.0/fd-v10.5.0-x86_64-unknown-linux-musl.tar.gz> |
| 资产大小 | 1.5 MiB（1573549 字节） |
| sha256 | `761c72dc8e120d85b22292063be8a796e2eeb20eb3e4f38b8fa2343ccf3514a7` |
| 架构 | `x86_64` |
| 归档形状 | tar.gz (musl，静态) |
| 归档里取的成员 | `fd-v10.5.0-x86_64-unknown-linux-musl/fd` |
| 落点（`__output/` 下） | `usr/bin/fdfind` |
| 命令名 | `fdfind` |
| 装完的版本串 | `fd 10.5.0`（实测 `fdfind --version` 的第一行） |
| license | **上游的：MIT OR Apache-2.0** —— 本仓库只做声明，**不分发二进制** |

> ⚠️ **注意**：上游是 **`sharkdp/fd`**，归档里的二进制叫 **`fd`**；本项目**故意**把项目目录和命令名都定为 **`fdfind`** —— Ubuntu 的 `fd-find` 包提供的命令就是 `fdfind`，用户机器上习惯/已有的也是它。所以 `member` 指向 `fd-v10.5.0-…/fd`、`dest` 是 `usr/bin/fdfind`。**没有另建一个 `fd` 项目**：同一个上游资产只声明一次，避免两个项目装同一个文件、`uninstall` 时互相踩（要 `fd` 就自己 `alias fd=fdfind` —— 本项目不改 `PATH`、也不建别名）。`fdfind --version` 打的是 `fd 10.5.0`（二进制里编进去的名字不会跟着 `dest` 改）。归档里还有 CHANGELOG / LICENSE-* / README / autocomplete，只有 member 那一个进 `__output/`。

## 怎么装

```sh
wtool download-release tools/musl-bins/fdfind   # 读 wtool.xml 的 <muslbin url>，按 sha256 校验 → __release/
wtool unpack-release   tools/musl-bins/fdfind   # 按 member/dest 解到 __output/usr/bin/fdfind
wtool install          tools/musl-bins/fdfind   # 建 L2 链：$WTOOL_HOME/usr/bin/fdfind
```

装完 `fdfind` 就能直接敲 —— `$WTOOL_HOME/usr/bin` 在 `PATH` 最前（ADR-0045 §1.2），
本项目**不自己往 PATH 里塞**。

> ⚠️ 头两条是**开发机命令**（D50）：有源码、能联网的机器用它们直接取上游。
> **断网机**不跑这两条 —— 它拿的是离线族的 `release-offline.zip`
> （解开 → `cp -a` 并进 `$WTOOL_HOME/wtool/` → `wtool install`）。

## 怎么升级（bump 三步）

1. **看上游新 tag 有没有 x86_64 的 musl/静态资产**：

   ```sh
   gh api repos/sharkdp/fd/releases --jq '.[0].tag_name, (.[0].assets[].name)'
   ```

   要的是 `x86_64-unknown-linux-musl`（Rust）或 `…_linux_x86_64` / `…_linux_amd64`
   （Go，`CGO_ENABLED=0` 编出来是静态的）。**没有就跳过这个版本**，
   **不要**拿 `-gnu` / `-glibc` 的顶上 —— 它依赖宿主 glibc，就失去这个项目存在的意义。
   
2. **下下来、现算 sha256**（**不许照抄任何地方的旧值**，包括本文件的；只落 `/tmp`）：

   ```sh
   id=$(gh api repos/sharkdp/fd/releases/tags/<新tag> \
        --jq '.assets[] | select(.name=="<新资产名>") | .id')
   curl -fsSL -H 'Accept: application/octet-stream' \
     "https://api.github.com/repos/sharkdp/fd/releases/assets/$id" -o /tmp/fdfind.dl
   sha256sum /tmp/fdfind.dl && stat -c %s /tmp/fdfind.dl
   tar tzf /tmp/fdfind.dl | head        # 或 unzip -l —— 确认 member 还对不对
   ```

   （走 API 的资产端点是**故意的**：`github.com` 的直链有时不通，这个端点稳定。）

3. **改两处**：`docs/tools.tsv` 那一行（tag / asset / sha256 / bytes / member），
   然后 `python3 scripts/gen-files.py fdfind` 重新生成 `wtool.xml`。
   本文件里那几条**只在本文件里有**的信息（版本串、注意事项）也要跟着更新。
   最后在**临时** `$WTOOL_HOME` 里把上面三条命令跑一遍，确认 `fdfind --version`
   打得出来 —— **别在真 `$HOME` 上试**。

## 为什么它进 `muslbin` 这个类型

上游发布的是**静态**二进制（Rust 的 `*-unknown-linux-musl`，或 Go 的
`CGO_ENABLED=0`）：不依赖宿主 glibc，同一份文件在 WSL、公司 Ubuntu 服务器上都能跑。
这正是 wtool 的使用场景（`harness/docs/adr/0045-wtool-redesign/pre_architecture.md` §4）。

判据不是"资产名里有没有 musl"，而是**`ldd` 认不认它**（认不出 = 静态）。
本仓库每个工具都实测过一遍（`tar.gz (musl，静态)`）。
