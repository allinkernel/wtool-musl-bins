# wtool-musl-bins

**② 类 `muslbin` 项目的集合**（ADR-0045 §1.4 / DESIGN D26）：

> 从**上游 release** 直接取 **x86_64 静态二进制**（Rust 的 `*-unknown-linux-musl`
> 或 Go 的 `CGO_ENABLED=0`），装到 `$WTOOL_HOME/usr/bin/` 下当命令用。

这个仓库**只有文本**：每个工具一个子目录，里面是 `wtool.xml` + `readme.md` +
`env.zsh` / `env.bash`。**二进制不进 git** —— 它们由 `wtool download-release`
从上游 release 页下下来，解到子目录的 `__output/usr/bin/` 下。

三类工具都在这里（第 ⑦.1 / ⑦.3 块）：

| 类 | 是什么 | 例子 |
|---|---|---|
| **A 档** | 纯二进制，装完就能敲 | `bat` / `jq` / `eza` … |
| **hook 类** | 除了二进制，还要往 shell 里注册函数/别名 → 用 `<generate>`（**安装时**生成 shell 集成，`env.{zsh,bash}` 去 source） | `fzf` / `zoxide` / `direnv` / `atuin` / `starship` / `navi` |
| **B 档** | 纯二进制，但要跑起来才知道有没有用（联网 / 看文件 / 大） | `rclone` / `miller` / `lf` / `micro` / `qsv` … |

## 为什么要有这个项目

`x86_64-musl` 的静态二进制**不依赖 glibc**，所以同一份文件在
WSL、公司 Ubuntu 服务器、任何发行版上都能跑 —— 这正是这台机器的使用场景
（见 `harness/docs/adr/0045-wtool-redesign/pre_architecture.md` §4）。

## 目录 = 一个 wtool 项目

```
tools/musl-bins/            ← 本仓库（GitHub: allinkernel/wtool-musl-bins）
├── README.md               ← 你正在读的这份（仓库总说明，不是 wtool 项目）
├── AGENTS.md               ← 给助手看的（工具目录规矩 / bump 三步 / 别做）
├── docs/tools.tsv          ← **唯一权威的工具表**（谁、哪个 tag、哪个资产、sha256、member、dest）
├── scripts/                ← 维护脚本（**不参与安装**）
│   ├── gen-files.py        ←   读 docs/tools.tsv → 生成每个工具的 wtool.xml + env.{zsh,bash}
│   ├── gen-readmes.py      ←   同上 → 生成每个工具的 readme.md + 本文件里那张工具总表
│   ├── env-skeleton.txt    ←   env.{zsh,bash} 的模板（两份逐字等价靠它保证）
│   └── versions.tsv        ←   实测的 `<命令> --version` 第一行（人读的佐证）
├── bat/                    ← 一个工具 = 一个 wtool 项目（第 ⑦.3 块之后 45 个）
│   ├── wtool.xml           ←   kind="muslbin" + <muslbin …> + <export_bin …>（hook 类还有 <generate>）
│   ├── readme.md           ←   这个二进制从哪来（项目 / release 页 / tag / 资产 / sha256 / license）
│   ├── env.zsh / env.bash  ←   两份逐字等价；本项目不往 PATH 里塞东西
│   └── __output/           ←   跑 `wtool download-release` + `unpack-release` 才有（不进 git）
├── eza/
└── …
```

**为什么一个工具一个 `wtool.xml`**：引擎按磁盘上的 `wtool.xml` 扫项目。
每个子目录各带一份，于是**每个工具都是独立项目** ——
可以单独 `wtool install tools/musl-bins/bat`，卸载也只影响它一个。

## 怎么加一个新工具

> 上游**必须有官方 musl/静态资产**。第三方重打包的一律不要
> （来源不可信、也没有稳定的 URL 与 sha256）。

1. **按 tag 找资产**（不要用 `latest`，`<muslbin tag=>` 要求钉死）：

   ```sh
   gh api repos/<owner>/<repo>/releases --jq '.[0].tag_name, (.[0].assets[].name)'
   # 想看全部版本：gh api repos/<owner>/<repo>/releases --paginate \
   #   --jq '.[] | select(.prerelease==false) | .tag_name as $t | .assets[] | "\($t)\t\(.name)"'
   ```

   要的是 `x86_64-unknown-linux-musl.tar.gz`（Rust）或 `…_linux_x86_64` / `…_linux_amd64`
   （Go，`CGO_ENABLED=0` 编出来是静态）。**没有就跳过这个工具**，
   别拿 `-gnu` / `-glibc` 的顶上（它依赖宿主 glibc，就失去这个项目存在的意义了）。

2. **真下下来、真算 sha256、真判它是不是静态**（**不许照抄记忆或别处的清单**）：

   ```sh
   id=$(gh api repos/<owner>/<repo>/releases/tags/<tag> \
        --jq '.assets[] | select(.name=="<资产名>") | .id')
   curl -fsSL -H 'Accept: application/octet-stream' \
     "https://api.github.com/repos/<owner>/<repo>/releases/assets/$id" -o /tmp/a
   sha256sum /tmp/a && stat -c %s /tmp/a
   tar tzf /tmp/a | head          # 或 unzip -l /tmp/a —— 看归档形状
   # ↓ 解出那个二进制再判：`ldd` 认不出来 = 静态（**这才是判据**，不是资产名）
   tar xzf /tmp/a -C /tmp <member> && file -b /tmp/<基名> && ldd /tmp/<基名>
   ```

3. **看归档里那个二进制叫什么**（决定 `member` / `dest` 怎么写）：

   - **裸二进制**（`jq-linux-amd64`、`yq_linux_amd64`、`shfmt_v3.14.1_linux_amd64`、
     `b3sum_linux_x64_bin` 这种，上游发的就是那个文件）→ `member` **不写**，`dest="usr/bin/<命令名>"`
   - **归档里那一个文件**（`eza` 的 `./eza`、`just` 的 `just`）→ `member="<归档内的路径>"`，
     `dest="usr/bin/<命令名>"`
   - **归档里多一层目录**（`bat`、`sd`、`dust`、`glow`、`fclones`…）→ `member` 写**全路径**
     （`bat-v0.26.1-…/bat`、`target/x86_64-unknown-linux-musl/release/fclones`）——
     声明式解包会**剥掉最后一个 `/` 之前的部分**，落到 `dest` 的就是那个文件名
   - ⚠️ **命令名可能和目录名不一样**：`bottom`→`btm`、`difftastic`→`difft`、`trippy`→`trip`。
     那种情况 `dest="usr/bin/btm"`，`<export_bin>` 跟着走（`name=` 可以省，因为
     `dest` 的 basename 已经对了）

4. **改表 + 生成**（**别手写 `<工具>/` 下的文件**，它们由表生成）：

   ```sh
   # ① docs/tools.tsv 加一行（或改一行）—— 这是唯一权威表
   #    带 shell 集成的工具（zoxide 这种）把命令写进最后一列 `generate`：
   #        zsh:zoxide init zsh;bash:zoxide init bash
   #    → gen-files.py 会连 <generate> 和 env 里的 source 块一起生成
   # ② 生成：
   python3 scripts/gen-files.py   <工具>     # → <工具>/{wtool.xml,env.zsh,env.bash}
   python3 scripts/gen-readmes.py <工具>     # → <工具>/readme.md
   # ③ 把实测的 `<命令> --version` 第一行补进 scripts/versions.tsv，再重跑 ②
   #    工具总表也一起刷新（README.md 里两个标记之间的那段）：
   python3 scripts/gen-readmes.py --table    # 打到 stdout，贴回 README.md
   # ④ 查漂移（CI 式的自查，三处都要 0 DRIFT）：
   python3 scripts/gen-files.py --check && python3 scripts/gen-readmes.py --check \
     && python3 scripts/gen-readmes.py --table --check
   ```

5. **验一遍**（在**临时** `$WTOOL_HOME` 里，别碰真 `$HOME`）：

   ```sh
   export WTOOL_HOME=$(mktemp -d)/.wtool WTOOL_STATE=$(mktemp -d)
   sh bootstrap/wtool.sh download-release tools/musl-bins/<工具>   # 按 <muslbin url=> 下 + sha256
   sh bootstrap/wtool.sh unpack-release   tools/musl-bins/<工具>   # 按 member=/dest= 解
   sh bootstrap/wtool.sh install          tools/musl-bins/<工具>
   readlink "$WTOOL_HOME/usr/bin/<命令名>"      # 应当是一条相对链
   "$WTOOL_HOME/usr/bin/<命令名>" --version
   sh bootstrap/wtool.sh uninstall tools/musl-bins/<工具>
   ```

   ⚠️ **hook 类**（`generate` 列非空）还要验 shell 集成：装完在
   **交互式** shell 里 source 一下项目的 `env.<shell>`，看函数有没有注册 ——

   ```sh
   env -i HOME=$HOME PATH=$PATH WTOOL_HOME=$WTOOL_HOME zsh -f -i -c \
     '. $WTOOL_HOME/wtool/tools/musl-bins/zoxide/env.zsh; typeset -f __zoxide_z'
   # 非交互（zsh -c 不带 -i）里一个定义都不会有 —— 那不是坏了
   ```

## 每个工具的来源

**唯一权威是 [`docs/tools.tsv`](docs/tools.tsv)**（脚本读它、检查也读它），
下表是人读版本 —— 每个工具子目录里的 `readme.md` 是**逐工具的展开版**
（含完整 URL、资产名、sha256、license、升级步骤）。

<!-- BEGIN TOOLS-TABLE（由 scripts/gen-readmes.py --table 生成，别手改这一段） -->
| 工具 | 命令 | 上游项目（release 页） | tag | 资产 | 静态？ |
|---|---|---|---|---|---|
| `bat` | `bat` | [sharkdp/bat](https://github.com/sharkdp/bat/releases/tag/v0.26.1) | `v0.26.1` | `bat-v0.26.1-x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `eza` | `eza` | [eza-community/eza](https://github.com/eza-community/eza/releases/tag/v0.23.5) | `v0.23.5` | `eza_x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `delta` | `delta` | [dandavison/delta](https://github.com/dandavison/delta/releases/tag/0.20.1) | `0.20.1` | `delta-0.20.1-x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `dust` | `dust` | [bootandy/dust](https://github.com/bootandy/dust/releases/tag/v1.2.6) | `v1.2.6` | `dust-v1.2.6-x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `duf` | `duf` | [muesli/duf](https://github.com/muesli/duf/releases/tag/v0.9.1) | `v0.9.1` | `duf_0.9.1_linux_x86_64.tar.gz` | tar.gz (Go，静态) |
| `procs` | `procs` | [dalance/procs](https://github.com/dalance/procs/releases/tag/v0.14.12) | `v0.14.12` | `procs-v0.14.12-x86_64-linux.zip` | zip (musl，静态) |
| `bottom` | `btm` | [ClementTsang/bottom](https://github.com/ClementTsang/bottom/releases/tag/0.14.9) | `0.14.9` | `bottom_x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `jq` | `jq` | [jqlang/jq](https://github.com/jqlang/jq/releases/tag/jq-1.8.2) | `jq-1.8.2` | `jq-linux-amd64` | tar 无（裸二进制，静态） |
| `gojq` | `gojq` | [itchyny/gojq](https://github.com/itchyny/gojq/releases/tag/v0.12.19) | `v0.12.19` | `gojq_v0.12.19_linux_amd64.tar.gz` | tar.gz (Go，静态) |
| `yq` | `yq` | [mikefarah/yq](https://github.com/mikefarah/yq/releases/tag/v4.54.1) | `v4.54.1` | `yq_linux_amd64` | tar 无（裸二进制，静态） |
| `sd` | `sd` | [chmln/sd](https://github.com/chmln/sd/releases/tag/v1.1.0) | `v1.1.0` | `sd-v1.1.0-x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `hyperfine` | `hyperfine` | [sharkdp/hyperfine](https://github.com/sharkdp/hyperfine/releases/tag/v2.0.0) | `v2.0.0` | `hyperfine-v2.0.0-x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `just` | `just` | [casey/just](https://github.com/casey/just/releases/tag/1.58.0) | `1.58.0` | `just-1.58.0-x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `scc` | `scc` | [boyter/scc](https://github.com/boyter/scc/releases/tag/v4.1.0) | `v4.1.0` | `scc_Linux_x86_64.tar.gz` | tar.gz (Go，静态) |
| `difftastic` | `difft` | [Wilfred/difftastic](https://github.com/Wilfred/difftastic/releases/tag/0.71.0) | `0.71.0` | `difft-0.71.0-x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `fclones` | `fclones` | [pkolaczk/fclones](https://github.com/pkolaczk/fclones/releases/tag/v0.35.0) | `v0.35.0` | `fclones-0.35.0-linux-musl-x86_64.tar.gz` | tar.gz (musl，静态) |
| `shellcheck` | `shellcheck` | [koalaman/shellcheck](https://github.com/koalaman/shellcheck/releases/tag/v0.11.0) | `v0.11.0` | `shellcheck-v0.11.0.linux.x86_64.tar.gz` | tar.gz (静态) |
| `shfmt` | `shfmt` | [mvdan/sh](https://github.com/mvdan/sh/releases/tag/v3.14.1) | `v3.14.1` | `shfmt_v3.14.1_linux_amd64` | tar 无（裸二进制，静态） |
| `age` | `age` | [FiloSottile/age](https://github.com/FiloSottile/age/releases/tag/v1.3.2) | `v1.3.2` | `age-v1.3.2-linux-amd64.tar.gz` | tar.gz (Go，静态) |
| `b3sum` | `b3sum` | [BLAKE3-team/BLAKE3](https://github.com/BLAKE3-team/BLAKE3/releases/tag/1.8.7) | `1.8.7` | `b3sum_linux_x64_bin` | tar 无（裸二进制，static-pie） |
| `glow` | `glow` | [charmbracelet/glow](https://github.com/charmbracelet/glow/releases/tag/v3.0.0) | `v3.0.0` | `glow_3.0.0_Linux_x86_64.tar.gz` | tar.gz (Go，静态) |
| `xh` | `xh` | [ducaale/xh](https://github.com/ducaale/xh/releases/tag/v0.26.2) | `v0.26.2` | `xh-v0.26.2-x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `gping` | `gping` | [orf/gping](https://github.com/orf/gping/releases/tag/gping-v1.21.0) | `gping-v1.21.0` | `gping-Linux-musl-x86_64.tar.gz` | tar.gz (musl，静态) |
| `trippy` | `trip` | [fujiapple852/trippy](https://github.com/fujiapple852/trippy/releases/tag/0.13.0) | `0.13.0` | `trippy-0.13.0-x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `yazi` | `yazi` | [sxyazi/yazi](https://github.com/sxyazi/yazi/releases/tag/v26.9.1) | `v26.9.1` | `yazi-x86_64-unknown-linux-musl.zip` | zip (musl，静态) |
| `zellij` | `zellij` | [zellij-org/zellij](https://github.com/zellij-org/zellij/releases/tag/v0.45.1) | `v0.45.1` | `zellij-x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `lazygit` | `lazygit` | [jesseduffield/lazygit](https://github.com/jesseduffield/lazygit/releases/tag/v0.66.1) | `v0.66.1` | `lazygit_0.66.1_linux_x86_64.tar.gz` | tar.gz (Go，静态) |
| `dive` | `dive` | [wagoodman/dive](https://github.com/wagoodman/dive/releases/tag/v0.13.1) | `v0.13.1` | `dive_0.13.1_linux_amd64.tar.gz` | tar.gz (Go，静态) |
| `fzf` | `fzf` | [junegunn/fzf](https://github.com/junegunn/fzf/releases/tag/v0.74.5) | `v0.74.5` | `fzf-0.74.5-linux_amd64.tar.gz` | tar.gz (Go，静态) |
| `zoxide` | `zoxide` | [ajeetdsouza/zoxide](https://github.com/ajeetdsouza/zoxide/releases/tag/v0.10.0) | `v0.10.0` | `zoxide-0.10.0-x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `direnv` | `direnv` | [direnv/direnv](https://github.com/direnv/direnv/releases/tag/v2.38.2) | `v2.38.2` | `direnv.linux-amd64` | tar 无（裸二进制，Go 静态） |
| `atuin` | `atuin` | [atuinsh/atuin](https://github.com/atuinsh/atuin/releases/tag/v18.23.0) | `v18.23.0` | `atuin-x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `starship` | `starship` | [starship/starship](https://github.com/starship/starship/releases/tag/v1.26.0) | `v1.26.0` | `starship-x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `navi` | `navi` | [denisidoro/navi](https://github.com/denisidoro/navi/releases/tag/v2.24.0) | `v2.24.0` | `navi-v2.24.0-x86_64-unknown-linux-musl.tar.gz` | tar.gz (musl，静态) |
| `rclone` | `rclone` | [rclone/rclone](https://github.com/rclone/rclone/releases/tag/v1.75.2) | `v1.75.2` | `rclone-v1.75.2-linux-amd64.zip` | zip (Go，静态) |
<!-- END TOOLS-TABLE -->


> **上表是 `docs/tools.tsv` 的渲染结果**（`scripts/gen-readmes.py` 用的同一份数据）——
> 每个工具子目录里的 `readme.md` 是逐工具的展开版（完整直链、sha256、license、升级步骤）。
>
> ### 验过但**没收进来**的（下面这一节就是"为什么没有它"的答案）
>
> | 工具 | 上游 | 为什么没收 |
> |---|---|---|
> | `tokei` | XAMPPRocky/tokei | `v15.0.0` 的 release **一个资产都没有**（`assets: []`）；官方从不发预编译二进制 |
> | `ast-grep` | ast-grep/ast-grep | 只有 `app-x86_64-unknown-linux-gnu.zip`；下下来实跑 `ldd` → 依赖 `libgcc_s` / `libm` / `libc`，**动态链接**，不是静态 |
> | `jless` | PaulJuliusMartinez/jless | 只有 `-x86_64-unknown-linux-gnu.zip`；实跑 `ldd` → `libxcb` / `libgcc_s` / `libc`，**动态链接** |
> | `bandwhich` | imsnif/bandwhich | `v0.23.1` 有 `-x86_64-unknown-linux-musl.tar.gz`（**静态，验过**），但它要 **root / `cap_net_raw,cap_net_admin`** 才抓得到包 —— 用户 2026-10-13 明确"要特殊权限的跳过"。要收就是个 `docs/tools.tsv` 加一行的事（`trippy` 是先例：收了 + readme 里写清 `setcap`） |
> | `lazydocker` | jesseduffield/lazydocker | `v0.25.2` 的 `lazydocker_0.25.2_Linux_x86_64.tar.gz`（Go 静态）本身合格，但它是**连 docker daemon 的 TUI**：目标机上没有/没权限连 socket 时它一行都显示不出来 → **跳过**（用户 2026-10-13 同意"依赖 docker/k8s 在跑的跳过"） |
> | `k9s` | derailed/k9s | 同上（要一个能连的 k8s 集群），而且 `k9s_Linux_amd64.tar.gz` 是 **41 MB** → 跳过 |
> | `nushell` | nushell/nushell | 官方的 `nu-0.116.1-x86_64-unknown-linux-musl.tar.gz` 是 **86 MB**（不是用户说的 ~50 MB）→ **体积过大，留给用户拍板** |
> | `ffmpeg` | FFmpeg/FFmpeg | 官方**根本不发二进制**（GitHub 上连 release 资产都没有，只有源码 tag）；网上那些"静态 ffmpeg"全是**第三方重打包**（johnvansickle / BtbN 之流）→ 按"只能第三方重打包的一律不收"**拒** |
>
> 判据不是"资产名里有没有 musl"，而是 **`file` + `ldd` 认不认它**。
> `age` 就是这条判据的反例：资产名里**没有** musl，但实测**没有动态段**（纯静态 Go）→ 收。
> 被拒的都不许用第三方重打包顶上（`AGENTS.md` 的"别做"）。

## 这个仓库不做什么

- **不放二进制**（`*.tar.gz` / `*.zip` / 编好的可执行文件都进 `.gitignore`）。
  唯一例外是 `scripts/*.sh`：几个上游归档多套了一层目录，
  需要**剥壳**才能得到裸二进制 —— 那是**安装期的声明**，不是二进制本身。
- **不装东西到 `$HOME`**：装是 `wtool install` 的事，落点是
  `$WTOOL_HOME/wtool/tools/musl-bins/<工具>/__output/` + 一条 L2 链
  `$WTOOL_HOME/usr/bin/<工具>`（ADR-0045 §1.3 / D37：**链，不是实体**）。
- **不改 `PATH`**：`$WTOOL_HOME/usr/bin` 由引擎统一放在最前（ADR-0045 §1.2），
  项目的 `env.{zsh,bash}` 不碰 `PATH`。

## 相关文档

- 设计：`harness/docs/adr/0045-wtool-redesign/DESIGN.md` §1.4 / §1.5 / D26 / D32 / D37
- 逐场景：`harness/docs/adr/0045-wtool-redesign/pre_architecture.md` §4（② muslbin 项目）
- 清单语法：`bootstrap/docs/manifest-schema.md` 的 `<muslbin>` 一节
