#!/bin/sh
# 生成 direnv 的 shell 集成，并把**二进制绝对路径**换成 ${WTOOL_HOME}。
#
# 为什么不能直接 `<generate cmd="direnv hook bash">`：
#   `direnv hook` 输出里带**二进制自己的绝对路径**（装在哪台机器就写哪台）。
#   整机包是一份"已经装好的 .wtool"，目标机**不会重跑** `<generate>`，
#   于是那份死路径被原样 source → 目标机上每条命令都报
#     bash: /home/<别人>/self/wtool/tools/musl-bins/direnv/__output/usr/bin/direnv: No such file or directory
#   （2026-10-21 用户 VM 实测；与 starship 那次同类）。
#
# 契约（引擎 `<generate cmd=>`）：cwd = 项目根（`tools/musl-bins/direnv`），
# PATH 前面是 `$WTOOL_HOME/usr/bin`，WTOOL_HOME / WTOOL_PROJECT_DIR 已导出；
# 本脚本的 stdout 就是生成物（必须非空，否则 install 当场失败）。
#
# 用法：sh ../../scripts/gen-direnv-hook.sh <bash|zsh>
set -eu

_sh=${1:-}
case $_sh in
    bash|zsh) ;;
    *) echo "用法：$0 <bash|zsh>" >&2; exit 2 ;;
esac

_bin="$WTOOL_HOME/usr/bin/direnv"
[ -x "$_bin" ] || {
    echo "direnv 不在 $_bin —— 它该由 <muslbin> + <export_bin> 先装到 \$WTOOL_HOME/usr/bin" >&2
    exit 1
}

# direnv 会把软链解析成真实路径再写进 hook，所以两种形式都要替换。
_real=$(readlink -f -- "$_bin" 2>/dev/null || printf '%s' "$_bin")

"$_bin" hook "$_sh" \
    | sed -e "s|$_real|\${WTOOL_HOME}/usr/bin/direnv|g" \
          -e "s|$_bin|\${WTOOL_HOME}/usr/bin/direnv|g"
