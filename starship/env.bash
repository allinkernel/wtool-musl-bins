# 由 $WTOOL_HOME/env.bash 里的 wtool 块 source。与 env.zsh 逐字等价
# （只有本条注释、报错里那句提示、和最后那个 source 行里的 shell 名不同）。
#
# starship 是**② 类 muslbin 项目**（ADR-0045 §1.4）：上游 release 的 x86_64 静态二进制，
# 由 `wtool download-release` 下到 __output/usr/bin/starship，再由 <export_bin>
# 建一条 L2 链 $WTOOL_HOME/usr/bin/starship。
#
# ⚠️ 本文件**不往 PATH 里塞东西**：$WTOOL_HOME/usr/bin 由引擎统一放最前
#    （ADR-0045 §1.2 / D48）。这个项目里绝大多数工具**一个变量都不需要** ——
#    留下这段是因为**装错了要能立刻看出来**：缺了它，症状是某个 shell 里
#    敲 `starship` 是 command not found，而 `wtool install` 明明说装好了
#    （那种半装状态最难查）。
if [ -z "${WTOOL_HOME:-}" ] || [ ! -d "$WTOOL_HOME" ]; then
    echo "wtool: WTOOL_HOME 未设置或不存在（当前值：'${WTOOL_HOME:-}'）。" >&2
    echo "       starship 的二进制在 $WTOOL_HOME/usr/bin/starship —— 没有 WTOOL_HOME 就找不到它。" >&2
    echo "       请在你的 ~/.bashrc 最后加上这两行（zsh 用 env.zsh）：" >&2
    echo "         export WTOOL_HOME=~/.wtool" >&2
    echo "         source \${WTOOL_HOME}/env.bash" >&2
    return 1 2>/dev/null || exit 1
fi

# ---------------------------------------------------------------------------
# shell 集成：**安装时生成**，这里只负责 source（D33 / D41）
#
# 生成物落在 __output/ 下（不是源码树）：它是**安装期产物**，不进 git。
# 生成它的命令写在 wtool.xml 里：
#     <generate dest="__output/starship.bash" cmd="starship init bash"/>
# `wtool install` 时跑（产物进账本）、`wtool uninstall` 时删。
#
# ‼️ 生成物读不到就**说一句再跳过**，绝不静默：静默的症状是"starship 装好了，
#    但 shell 集成没生效"，而这里一声不吭 —— 和本文件顶部那段是同一个理由
#    （半装状态最难查）。真装过的话它一定在。
# ---------------------------------------------------------------------------
# 单独 source（不经 wtool 块）时的兜底：L1 路径就是项目在 $WTOOL_HOME 里的稳定地址
[ -n "${WTOOL_PROJECT_DIR:-}" ] || WTOOL_PROJECT_DIR="$WTOOL_HOME/wtool/tools/musl-bins/starship"
WTOOL_STARSHIP_RC="$WTOOL_PROJECT_DIR/__output/starship.bash"
if [ -r "$WTOOL_STARSHIP_RC" ]; then
    source "$WTOOL_STARSHIP_RC"
else
    echo "wtool: starship 的 shell 集成还没生成：$WTOOL_STARSHIP_RC" >&2
    echo "       它是 wtool install 时按 wtool.xml 的 <generate> 生成的；" >&2
    echo "       跑一次 wtool install tools/musl-bins/starship 就有了（不用重下二进制）。" >&2
fi
unset WTOOL_STARSHIP_RC
