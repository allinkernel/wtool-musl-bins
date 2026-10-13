# 由 $WTOOL_HOME/env.bash 里的 wtool 块 source。与 env.zsh 逐字等价
# （只有本条注释、报错里那句提示、和最后那个 source 行里的 shell 名不同）。
#
# xh 是**② 类 muslbin 项目**（ADR-0045 §1.4）：上游 release 的 x86_64 静态二进制，
# 由 `wtool download-release` 下到 __output/usr/bin/xh，再由 <export_bin>
# 建一条 L2 链 $WTOOL_HOME/usr/bin/xh。
#
# ⚠️ 本文件**不往 PATH 里塞东西**：$WTOOL_HOME/usr/bin 由引擎统一放最前
#    （ADR-0045 §1.2 / D48）。这个项目里绝大多数工具**一个变量都不需要** ——
#    留下这段是因为**装错了要能立刻看出来**：缺了它，症状是某个 shell 里
#    敲 `xh` 是 command not found，而 `wtool install` 明明说装好了
#    （那种半装状态最难查）。
if [ -z "${WTOOL_HOME:-}" ] || [ ! -d "$WTOOL_HOME" ]; then
    echo "wtool: WTOOL_HOME 未设置或不存在（当前值：'${WTOOL_HOME:-}'）。" >&2
    echo "       xh 的二进制在 $WTOOL_HOME/usr/bin/xh —— 没有 WTOOL_HOME 就找不到它。" >&2
    echo "       请在你的 ~/.bashrc 最后加上这两行（zsh 用 env.zsh）：" >&2
    echo "         export WTOOL_HOME=~/.wtool" >&2
    echo "         source \${WTOOL_HOME}/env.bash" >&2
    return 1 2>/dev/null || exit 1
fi
