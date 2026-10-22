# `qsv` —— dathere/qsv 的 x86_64 静态二进制

> 这份文件是**给人读的来源说明**。机器读的是同目录的 `wtool.xml`（下载声明）
> 和仓库根目录的 `docs/tools.tsv`（**唯一权威表**，wtool.xml 由它生成）。
> ⚠️ 两处的 **tag 与 sha256 必须一致** —— 改一处没改另一处 = 装的和你以为的不是一个东西。

## 这个二进制从哪来

| 项 | 值 |
|---|---|
| 上游项目 | [`dathere/qsv`](https://github.com/dathere/qsv) |
| **release 页** | <https://github.com/dathere/qsv/releases/tag/24.0.0> |
| 本仓库钉的 tag | `24.0.0` |
| 资产文件名 | `qsv-24.0.0-x86_64-unknown-linux-musl.zip` |
| 资产直链 | <https://github.com/dathere/qsv/releases/download/24.0.0/qsv-24.0.0-x86_64-unknown-linux-musl.zip> |
| 资产大小 | 53.6 MiB（56233031 字节） |
| sha256 | `0079acb8542af8b243fa861259746a6a88cef1aefc07214aaaf0f0a1b0593738` |
| 架构 | `x86_64` |
| 归档形状 | zip (musl，静态) |
| 归档里取的成员 | `qsv` |
| 落点（`__output/` 下） | `usr/bin/qsv` |
| 命令名 | `qsv` |
| 装完的版本串 | `qsv 24.0.0-jemalloc+bgthread-apply;fetch;foreach;self_update-32-32;19.56 GiB-64.00 GiB-18.59 GiB-24.45 GiB (x86_64-unknown-linux-musl compiled with Rust 1.99;Linux (Ubuntu 24.04)-Linux 6.6.87.2-microsoft-standard-WSL2;AMD Ryzen 9 5950X 16-Core Processor-16) prebuilt`（实测 `qsv --version` 的第一行） |
| license | **上游的：MIT** —— 本仓库只做声明，**不分发二进制** |

> ⚠️ **注意**：B 档。⚠️ **体积**：这个 zip 是 **56 MB**（本仓库最大的一份）—— 收它是**按 `qsv` 的官方静态资产存在**这条判据收的，体积这一条**请用户拍板**（不要就删掉 `docs/tools.tsv` 里那一行 + 这个目录）。包里还有 `qsvdp`（datapusher 精简版）/ `qsvlite` 两个变体与 `COPYING` / `LICENSE-MIT` / `README` / `THIRD_PARTY_NOTICES.md` —— **只取 `qsv` 本体**（本项目一个命令，别的变体要就另开子目录）。`qsv --version` 那一行很长（带构建特性与机器信息），`versions.tsv` 里如实存着。

## 怎么装

```sh
wtool download-release tools/musl-bins/qsv   # 读 wtool.xml 的 <muslbin url>，按 sha256 校验 → __release/
wtool unpack-release   tools/musl-bins/qsv   # 按 member/dest 解到 __output/usr/bin/qsv
wtool install          tools/musl-bins/qsv   # 建 L2 链：$WTOOL_HOME/usr/bin/qsv
```

装完 `qsv` 就能直接敲 —— `$WTOOL_HOME/usr/bin` 在 `PATH` 最前（ADR-0045 §1.2），
本项目**不自己往 PATH 里塞**。

> ⚠️ 头两条是**开发机命令**（D50）：有源码、能联网的机器用它们直接取上游。
> **断网机**不跑这两条 —— 它拿的是离线族的 `release-offline.zip`
> （解开 → `cp -a` 并进 `$WTOOL_HOME/wtool/` → `wtool install`）。

## 怎么升级（bump 三步）

1. **看上游新 tag 有没有 x86_64 的 musl/静态资产**：

   ```sh
   gh api repos/dathere/qsv/releases --jq '.[0].tag_name, (.[0].assets[].name)'
   ```

   要的是 `x86_64-unknown-linux-musl`（Rust）或 `…_linux_x86_64` / `…_linux_amd64`
   （Go，`CGO_ENABLED=0` 编出来是静态的）。**没有就跳过这个版本**，
   **不要**拿 `-gnu` / `-glibc` 的顶上 —— 它依赖宿主 glibc，就失去这个项目存在的意义。
   
2. **下下来、现算 sha256**（**不许照抄任何地方的旧值**，包括本文件的；只落 `/tmp`）：

   ```sh
   id=$(gh api repos/dathere/qsv/releases/tags/<新tag> \
        --jq '.assets[] | select(.name=="<新资产名>") | .id')
   curl -fsSL -H 'Accept: application/octet-stream' \
     "https://api.github.com/repos/dathere/qsv/releases/assets/$id" -o /tmp/qsv.dl
   sha256sum /tmp/qsv.dl && stat -c %s /tmp/qsv.dl
   tar tzf /tmp/qsv.dl | head        # 或 unzip -l —— 确认 member 还对不对
   ```

   （走 API 的资产端点是**故意的**：`github.com` 的直链有时不通，这个端点稳定。）

3. **改两处**：`docs/tools.tsv` 那一行（tag / asset / sha256 / bytes / member），
   然后 `python3 scripts/gen-files.py qsv` 重新生成 `wtool.xml`。
   本文件里那几条**只在本文件里有**的信息（版本串、注意事项）也要跟着更新。
   最后在**临时** `$WTOOL_HOME` 里把上面三条命令跑一遍，确认 `qsv --version`
   打得出来 —— **别在真 `$HOME` 上试**。

## 为什么它进 `muslbin` 这个类型

上游发布的是**静态**二进制（Rust 的 `*-unknown-linux-musl`，或 Go 的
`CGO_ENABLED=0`）：不依赖宿主 glibc，同一份文件在 WSL、公司 Ubuntu 服务器上都能跑。
这正是 wtool 的使用场景（`harness/docs/adr/0045-wtool-redesign/pre_architecture.md` §4）。

判据不是"资产名里有没有 musl"，而是**`ldd` 认不认它**（认不出 = 静态）。
本仓库每个工具都实测过一遍（`zip (musl，静态)`）。
