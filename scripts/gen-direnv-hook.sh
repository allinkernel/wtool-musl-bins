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

# ⚠️ 关键：direnv 把路径包在 **`$'…'`（ANSI-C 引用）** 里 ——
#     vars="$($'/real/path/direnv' export bash)";
#   `$'…'` 里 **不做参数展开**！所以只替换字符串会得到一个**字面量**
#   `${WTOOL_HOME}/usr/bin/direnv`，目标机上每条命令都报
#     _direnv_hook:5: no such file or directory: ${WTOOL_HOME}/usr/bin/direnv
#   （2026-10-21 用户 VM 实测，第二轮）。
#   必须把**整个 `$'<path>'` 记号**换成 `"${WTOOL_HOME}/usr/bin/direnv"`（双引号才展开）。
_pat() {   # <路径> → 打印 sed 表达式（四种包法都换成双引号形式）
    printf '%s\n' \
        "s|\\\$'$1'|\"\${WTOOL_HOME}/usr/bin/direnv\"|g" \
        "s|\"$1\"|\"\${WTOOL_HOME}/usr/bin/direnv\"|g" \
        "s|'$1'|\"\${WTOOL_HOME}/usr/bin/direnv\"|g" \
        "s|$1|\"\${WTOOL_HOME}/usr/bin/direnv\"|g"
}

{ _pat "$_real"; _pat "$_bin"; } > /tmp/.gen-direnv-hook.sed.$$
"$_bin" hook "$_sh" | sed -f /tmp/.gen-direnv-hook.sed.$$
_rc=$?
rm -f /tmp/.gen-direnv-hook.sed.$$
exit $_rc
