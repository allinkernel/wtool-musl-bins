# `zoxide` —— ajeetdsouza/zoxide 的 x86_64 静态二进制

> 这份文件是**给人读的来源说明**。机器读的是同目录的 `wtool.xml`（下载声明）
> 和仓库根目录的 `docs/tools.tsv`（**唯一权威表**，wtool.xml 由它生成）。
> ⚠️ 两处的 **tag 与 sha256 必须一致** —— 改一处没改另一处 = 装的和你以为的不是一个东西。

## 这个二进制从哪来

| 项 | 值 |
|---|---|
| 上游项目 | [`ajeetdsouza/zoxide`](https://github.com/ajeetdsouza/zoxide) |
| **release 页** | <https://github.com/ajeetdsouza/zoxide/releases/tag/v0.10.0> |
| 本仓库钉的 tag | `v0.10.0` |
| 资产文件名 | `zoxide-0.10.0-x86_64-unknown-linux-musl.tar.gz` |
| 资产直链 | <https://github.com/ajeetdsouza/zoxide/releases/download/v0.10.0/zoxide-0.10.0-x86_64-unknown-linux-musl.tar.gz> |
| 资产大小 | 0.6 MiB（591384 字节） |
| sha256 | `2d93385b99f3e82cf2701609a1bffcad863fbeb75aa3fe7eb6be4d29be68b1ae` |
| 架构 | `x86_64` |
| 归档形状 | tar.gz (musl，静态) |
| 归档里取的成员 | `zoxide` |
| 落点（`__output/` 下） | `usr/bin/zoxide` |
| 命令名 | `zoxide` |
| 装完的版本串 | `zoxide 0.10.0`（实测 `zoxide --version` 的第一行） |
| license | **上游的：MIT** —— 本仓库只做声明，**不分发二进制** |
| shell 集成（`<generate>`，D33） | `zoxide init zsh` / `zoxide init bash` —— **安装时**生成到 `__output/zoxide.{zsh,bash}`，由本项目自己的 `env.{zsh,bash}` 去 source |

> ⚠️ **注意**：归档里**也有** `completions/zoxide.{bash,fish,nu,ps1,ts,elv}` 和 man 页，但本项目**不用它们** —— shell 集成是 `<generate>` 在**安装时**跑 `zoxide init <shell>` 现生成的（D33）：补全、`z` / `zi` 别名、`chpwd` 钩子（`__zoxide_hook`）都在那份产物里。装完 `z` / `zi` 就可用，但 `zoxide` 得先在数据库里攒过目录（`zoxide add`）才有东西可跳。

## 怎么装

```sh
wtool download-release tools/musl-bins/zoxide   # 读 wtool.xml 的 <muslbin url>，按 sha256 校验 → __release/
wtool unpack-release   tools/musl-bins/zoxide   # 按 member/dest 解到 __output/usr/bin/zoxide
wtool install          tools/musl-bins/zoxide   # 建 L2 链：$WTOOL_HOME/usr/bin/zoxide
```

> ⚠️ **这个项目带 `<generate>`**：`wtool install` 的时候会跑 `zoxide init zsh` / `zoxide init bash`，
> 把输出写到 `__output/zoxide.zsh` / `__output/zoxide.bash`（进账本，`wtool uninstall` 删掉）。
> `env.zsh` / `env.bash` 各自 source 自己那一份 —— 所以 shell 集成是
> **装的时候**才有的，**不是** source 的时候现算的。

装完 `zoxide` 就能直接敲 —— `$WTOOL_HOME/usr/bin` 在 `PATH` 最前（ADR-0045 §1.2），
本项目**不自己往 PATH 里塞**。

> ⚠️ 头两条是**开发机命令**（D50）：有源码、能联网的机器用它们直接取上游。
> **断网机**不跑这两条 —— 它拿的是离线族的 `release-offline.zip`
> （解开 → `cp -a` 并进 `$WTOOL_HOME/wtool/` → `wtool install`）。

## 怎么升级（bump 三步）

1. **看上游新 tag 有没有 x86_64 的 musl/静态资产**：

   ```sh
   gh api repos/ajeetdsouza/zoxide/releases --jq '.[0].tag_name, (.[0].assets[].name)'
   ```

   要的是 `x86_64-unknown-linux-musl`（Rust）或 `…_linux_x86_64` / `…_linux_amd64`
   （Go，`CGO_ENABLED=0` 编出来是静态的）。**没有就跳过这个版本**，
   **不要**拿 `-gnu` / `-glibc` 的顶上 —— 它依赖宿主 glibc，就失去这个项目存在的意义。
   
2. **下下来、现算 sha256**（**不许照抄任何地方的旧值**，包括本文件的；只落 `/tmp`）：

   ```sh
   id=$(gh api repos/ajeetdsouza/zoxide/releases/tags/<新tag> \
        --jq '.assets[] | select(.name=="<新资产名>") | .id')
   curl -fsSL -H 'Accept: application/octet-stream' \
     "https://api.github.com/repos/ajeetdsouza/zoxide/releases/assets/$id" -o /tmp/zoxide.dl
   sha256sum /tmp/zoxide.dl && stat -c %s /tmp/zoxide.dl
   tar tzf /tmp/zoxide.dl | head        # 或 unzip -l —— 确认 member 还对不对
   ```

   （走 API 的资产端点是**故意的**：`github.com` 的直链有时不通，这个端点稳定。）

3. **改两处**：`docs/tools.tsv` 那一行（tag / asset / sha256 / bytes / member），
   然后 `python3 scripts/gen-files.py zoxide` 重新生成 `wtool.xml`。
   本文件里那几条**只在本文件里有**的信息（版本串、注意事项）也要跟着更新。
   最后在**临时** `$WTOOL_HOME` 里把上面三条命令跑一遍，确认 `zoxide --version`
   打得出来 —— **别在真 `$HOME` 上试**。

## 为什么它进 `muslbin` 这个类型

上游发布的是**静态**二进制（Rust 的 `*-unknown-linux-musl`，或 Go 的
`CGO_ENABLED=0`）：不依赖宿主 glibc，同一份文件在 WSL、公司 Ubuntu 服务器上都能跑。
这正是 wtool 的使用场景（`harness/docs/adr/0045-wtool-redesign/pre_architecture.md` §4）。

判据不是"资产名里有没有 musl"，而是**`ldd` 认不认它**（认不出 = 静态）。
本仓库每个工具都实测过一遍（`tar.gz (musl，静态)`）。
